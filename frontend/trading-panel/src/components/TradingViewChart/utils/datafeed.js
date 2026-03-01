// ========================================
// v2.0 订阅键格式管理
// 格式: {EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]
// 示例:
//   - BINANCE:BTCUSDT@KLINE_1      - 1分钟K线
//   - BINANCE:BTCUSDT@KLINE_60    - 1小时K线
//   - BINANCE:BTCUSDT@QUOTES      - 报价数据
//   - BINANCE:BTCUSDT@TRADE       - 实时交易
//   - BINANCE:BTCUSDT.PERP@KLINE_1 - 永续合约K线
//   - BINANCE:ACCOUNT@SPOT        - 现货账户信息
//   - BINANCE:ACCOUNT@FUTURES     - 期货账户信息
// ========================================

const DataType = {
    KLINE: 'KLINE',
    QUOTES: 'QUOTES',
    TRADE: 'TRADE',
    ACCOUNT: 'ACCOUNT'
};

/**
 * 构建 v2.0 格式的订阅键
 * @param {string} exchange - 交易所代码（如 BINANCE）
 * @param {string} symbol - 交易符号（如 BTCUSDT 或 BTCUSDT.PERP），账户类型用 ACCOUNT@SPOT 或 ACCOUNT@FUTURES
 * @param {string} dataType - 数据类型（KLINE, QUOTES, TRADE, ACCOUNT）
 * @param {string} [interval] - K线周期（可选，如 '1', '60'）
 * @returns {string} v2.0 格式的订阅键
 */
function buildSubscriptionKey(exchange, symbol, dataType, interval = null) {
    // 账户类型订阅键格式: BINANCE:ACCOUNT@SPOT 或 BINANCE:ACCOUNT@FUTURES
    if (dataType === DataType.ACCOUNT) {
        return `${exchange}:${symbol}@${dataType}`;
    }
    const baseKey = `${exchange}:${symbol}@${dataType}`;
    if (dataType === DataType.KLINE && interval) {
        return `${baseKey}_${interval}`;
    }
    return baseKey;
}

/**
 * 解析 v2.0 格式的订阅键
 * @param {string} subscriptionKey - v2.0 格式的订阅键
 * @returns {Object} 解析结果 { exchange, symbol, dataType, interval }
 */
function parseSubscriptionKey(subscriptionKey) {
    // 匹配格式: EXCHANGE:SYMBOL@DATA_TYPE 或 EXCHANGE:SYMBOL@DATA_TYPE_INTERVAL
    const match = subscriptionKey.match(/^([^:]+):([^@]+)@([A-Z]+)(?:_(.+))?$/);

    if (!match) {
        console.warn(`⚠️ 无法解析订阅键格式: ${subscriptionKey}`);
        return null;
    }

    return {
        exchange: match[1],
        symbol: match[2],
        dataType: match[3],
        interval: match[4] || null
    };
}

/**
 * 从 TradingView symbolInfo 构建订阅键
 * @param {Object} symbolInfo - TradingView 标的信息对象
 * @param {string} dataType - 数据类型（KLINE, QUOTES, TRADE）
 * @param {string} [interval] - K线周期（可选）
 * @returns {string} v2.0 格式的订阅键
 */
function buildKeyFromSymbolInfo(symbolInfo, dataType, interval = null) {
    // symbolInfo.ticker 格式: EXCHANGE:SYMBOL（如 BINANCE:BTCUSDT）
    const ticker = symbolInfo.ticker || symbolInfo.name || '';
    const [exchange, ...symbolParts] = ticker.split(':');
    const symbol = symbolParts.join(':') || symbolParts[0];

    return buildSubscriptionKey(exchange, symbol, dataType, interval);
}

// ========================================
// WebSocket 请求状态管理 - 三阶段模式
// ========================================

// 请求状态枚举
const RequestState = {
    PENDING: 'pending',       // 已发送，等待 ack
    ACKNOWLEDGED: 'acked',    // 已收到 ack，等待结果
    COMPLETED: 'completed',   // 已收到结果
    TIMEOUT: 'timeout'        // 超时
};

// 挂起的请求映射 (requestId -> 请求状态对象)
// 包含状态、ack回调、result回调、超时定时器等信息
const pendingRequests = new Map();

// 挂起的请求队列（WebSocket未连接时缓存）
const pendingRequestsQueue = [];

/**
 * 生成唯一请求ID
 */
function generateRequestId() {
    return `req_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
}

/**
 * 处理请求超时
 * @param {string} requestId - 请求ID
 */
function handleRequestTimeout(requestId) {
    const request = pendingRequests.get(requestId);
    if (!request) return;

    // 如果请求已完成（已收到响应），忽略超时
    if (request.state === RequestState.COMPLETED) {
        return;
    }

    // 更新状态为超时
    request.state = RequestState.TIMEOUT;

    // 清理超时定时器
    if (request.timeoutId) {
        clearTimeout(request.timeoutId);
        request.timeoutId = null;
    }

    // 通知 resultCallback 超时
    if (request.resultCallback) {
        request.resultCallback({
            action: 'error',
            type: request.type,
            requestId: requestId,
            error: { code: 'TIMEOUT', message: 'Request timeout' }
        });
    }

    // 标记请求已处理，但不删除，以便处理可能延迟到达的响应
    request.state = RequestState.COMPLETED;
    request.timedOut = true;

    console.log(`⏱️ 请求超时: ${requestId}, 延迟响应将被忽略`);
}

/**
 * 处理 ACK 确认
 * @param {string} requestId - 请求ID
 * @param {Object} messageData - 确认消息数据
 */
function handleAck(requestId, messageData) {
    const request = pendingRequests.get(requestId);
    if (!request) {
        console.warn(`⚠️ 收到未知请求的 ACK: ${requestId}`);
        return;
    }

    // 更新状态为已确认
    request.state = RequestState.ACKNOWLEDGED;

    // 调用 ack 回调（如果注册了）
    if (request.ackCallback) {
        request.ackCallback(messageData);
    }

    console.log(`✅ ACK 已处理: ${requestId}`);
}

/**
 * 处理请求成功响应
 * @param {string} requestId - 请求ID
 * @param {Object} messageData - 响应数据
 * @param {string} dataType - v2.0 协议数据类型 (如 CONFIG_DATA, KLINES_DATA)
 */
function handleSuccess(requestId, messageData, dataType) {
    const request = pendingRequests.get(requestId);
    if (!request) {
        // 请求可能已超时被标记为完成，但仍在pendingRequests中
        console.warn(`⚠️ 收到未知请求的 Success: ${requestId}`);
        return;
    }

    // 如果请求已超时完成，忽略此响应
    if (request.timedOut) {
        console.log(`⏭️ 忽略延迟到达的响应（请求已超时）: ${requestId}`);
        return;
    }

    // 更新状态为完成
    request.state = RequestState.COMPLETED;

    // 清理超时定时器
    if (request.timeoutId) {
        clearTimeout(request.timeoutId);
        request.timeoutId = null;
    }

    // 调用 result 回调
    // v2.0 协议: 传递实际数据类型 (dataType)
    if (request.resultCallback) {
        request.resultCallback({
            action: 'success',
            type: dataType || request.type,
            requestId: requestId,
            data: messageData
        });
    }

    // 标记请求已处理，但不删除，以便处理可能延迟到达的其他响应
    console.log(`🎉 请求成功完成: ${requestId}, dataType: ${dataType}`);
}

/**
 * 处理请求错误响应
 * @param {string} requestId - 请求ID
 * @param {Object} messageData - 错误数据
 */
function handleError(requestId, messageData) {
    const request = pendingRequests.get(requestId);
    if (!request) {
        // 请求可能已超时被标记为完成
        console.warn(`⚠️ 收到未知请求的 Error: ${requestId}`);
        return;
    }

    // 如果请求已超时完成，忽略此响应
    if (request.timedOut) {
        console.log(`⏭️ 忽略延迟到达的错误响应（请求已超时）: ${requestId}`);
        return;
    }

    // 更新状态为完成
    request.state = RequestState.COMPLETED;

    // 清理超时定时器
    if (request.timeoutId) {
        clearTimeout(request.timeoutId);
        request.timeoutId = null;
    }

    // 调用 result 回调
    if (request.resultCallback) {
        request.resultCallback({
            action: 'error',
            type: request.type,
            requestId: requestId,
            error: messageData || { code: 'UNKNOWN_ERROR', message: 'Unknown error' }
        });
    }

    // 移除请求记录
    pendingRequests.delete(requestId);
    console.log(`❌ 请求错误: ${requestId}`, messageData);
}

/**
 * 处理实时数据推送 - v2.1 订阅键格式解析
 * @param {Object} data - v2.1 格式的推送消息（包含 data.subscriptionKey 和 data.content）
 */
function handleUpdate(data) {
    // v2.1: 从 data.data 中提取 subscriptionKey 和 content
    const { subscriptionKey, content } = data.data;

    if (!subscriptionKey) {
        console.warn('⚠️ handleUpdate: 收到无效消息，缺少 subscriptionKey');
        return;
    }

    // 解析 v2.0 格式的订阅键
    const parsedKey = parseSubscriptionKey(subscriptionKey);
    if (!parsedKey) {
        console.warn(`⚠️ handleUpdate: 无法解析订阅键: ${subscriptionKey}`);
        return;
    }

    const { exchange, symbol, dataType, interval } = parsedKey;

    // 处理 KLINE 数据推送
    if (dataType === DataType.KLINE) {
        // 查找匹配的订阅者
        for (const [, subscription] of subscriptions.entries()) {
            // 从 ticker 中提取 symbol 进行比较
            const subTicker = subscription.symbolInfo?.ticker || subscription.symbol || '';
            const subSymbolParts = subTicker.split(':');
            const subSymbol = subSymbolParts.length > 1 ? subSymbolParts[1] : subSymbolParts[0];

            if (subSymbol === symbol && subscription.resolution === interval) {
                subscription.onRealtimeCallback(content);
                break;
            }
        }
    }
    // 处理 QUOTES 数据推送
    else if (dataType === DataType.QUOTES) {
        const fullSymbol = subscriptionKey.replace('@QUOTES', '');

        // content 可能是单个对象或数组（支持批量推送）
        const quoteDataArray = Array.isArray(content) ? content : [content];

        quotesSubscriptions.forEach((subscription) => {
            if (subscription.symbols) {
                let symbolMatch = false;

                // 尝试完整格式匹配
                if (subscription.symbols.includes(fullSymbol)) {
                    symbolMatch = true;
                } else {
                    // 尝试简化格式匹配（不带交易所前缀）
                    const simplifiedSymbol = fullSymbol.includes(':') ? fullSymbol.split(':')[1] : fullSymbol;
                    if (subscription.symbols.includes(simplifiedSymbol)) {
                        symbolMatch = true;
                    }
                }

                if (symbolMatch) {
                    // 传递数组格式以匹配 watchlist 期望
                    subscription.onRealtimeCallback(quoteDataArray);
                }
            }
        });
    }
    // 处理 TRADE 数据推送
    else if (dataType === DataType.TRADE) {
        // TODO: 根据需要实现 TRADE 数据的处理逻辑
        // 可扩展：添加 tradeSubscriptions 映射来管理实时交易订阅
        console.debug(`📊 TRADE 数据推送: ${symbol}`, content);
    }
    // 未知数据类型
    else {
        console.warn(`⚠️ handleUpdate: 未知数据类型 ${dataType}，订阅键: ${subscriptionKey}`);
    }
}

/**
 * 发送WebSocket请求（支持三阶段模式）
 * @param {Object} data - 请求数据（包含type字段）
 * @param {Function} resultCallback - 结果回调函数
 * @param {Function} ackCallback - ACK回调函数（可选）
 * @param {Number} timeout - 超时时间（默认10000ms）
 */
function sendWSRequest(data, resultCallback, ackCallback = null, timeout = 10000) {
    // 确保WebSocket已连接
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        // 缓存请求，连接建立后自动发送
        pendingRequestsQueue.push({ data, resultCallback, ackCallback, timeout });
        connectWebSocket().then(() => {
            processPendingRequestsQueue();
        });
        return;
    }

    const requestId = generateRequestId();

    // v2.0 协议: 使用 type 字段替代 action 字段
    // 将 data.type 映射到协议请求类型
    const dataType = data.type;
    const typeMap = {
        'config': 'GET_CONFIG',
        'search_symbols': 'GET_SEARCH_SYMBOLS',
        'resolve_symbol': 'GET_RESOLVE_SYMBOL',
        'klines': 'GET_KLINES',
        'quotes': 'GET_QUOTES',
        'server_time': 'GET_SERVER_TIME',
        'subscribe': 'SUBSCRIBE',
        'unsubscribe': 'UNSUBSCRIBE',
        'get_subscriptions': 'GET_SUBSCRIPTIONS',
    };

    const message = {
        protocolVersion: "2.0",
        type: typeMap[dataType] || dataType,
        requestId: requestId,
        timestamp: Date.now(),
        data: data
    };

    // 设置超时定时器
    const timeoutId = setTimeout(() => {
        handleRequestTimeout(requestId);
    }, timeout);

    // 注册请求状态
    pendingRequests.set(requestId, {
        type: data.type,
        state: RequestState.PENDING,
        ackCallback: ackCallback,
        resultCallback: resultCallback,
        timeoutId: timeoutId,
        startTime: Date.now(),
        timeout: timeout
    });

    console.log(`📤 发送请求: ${requestId}, type: ${data.type}, symbol: ${data.symbol || 'N/A'}`);

    // 发送消息
    try {
        ws.send(JSON.stringify(message));
    } catch (error) {
        clearTimeout(timeoutId);
        pendingRequests.delete(requestId);
        // v2.0 协议: 错误通过 type: 'ERROR' 传递，但本地错误仍使用 action 保持兼容
        resultCallback({
            action: 'error',
            type: data.type,
            requestId: requestId,
            error: { code: 'SEND_FAILED', message: error.message }
        });
    }
}

/**
 * 处理队列中的请求
 */
function processPendingRequestsQueue() {
    if (pendingRequestsQueue.length === 0) return;

    while (pendingRequestsQueue.length > 0) {
        const { data, resultCallback, ackCallback, timeout } = pendingRequestsQueue.shift();
        sendWSRequest(data, resultCallback, ackCallback, timeout);
    }
}

/**
 * 将 TradingView 的 resolution 转换为毫秒数
 * @param {string} resolution - 时间周期（1, 5, 15, 60, 240, 1D, 1W, 1M）
 * @returns {number} 毫秒数
 */
function resolutionToMs(resolution) {
    const resStr = String(resolution);
    if (resStr.includes('D')) {
        const days = parseInt(resStr) || 1;
        return days * 24 * 60 * 60 * 1000;
    }
    if (resStr.includes('W')) {
        const weeks = parseInt(resStr) || 1;
        return weeks * 7 * 24 * 60 * 60 * 1000;
    }
    if (resStr.includes('M')) {
        const months = parseInt(resStr) || 1;
        return months * 30 * 24 * 60 * 60 * 1000; // 近似30天
    }
    // 默认为分钟
    const minutes = parseInt(resStr) || 1;
    return minutes * 60 * 1000;
}

// 数据源配置缓存
let datafeedConfiguration = null;

// 订阅管理映射 - 使用 Map 存储所有活跃订阅
// 键: subscriberUID, 值: 订阅信息对象
const subscriptions = new Map();

// Quotes 订阅管理映射 - 使用 Map 存储所有活跃的报价订阅
// 键: listenerGUID, 值: 订阅信息对象
const quotesSubscriptions = new Map();

// 全局已订阅的 subscriptionKey 跟踪 - 避免重复订阅
// 键: subscriptionKey (如 BINANCE:BTCUSDT@QUOTES), 值: 引用计数
const subscribedQuotes = new Map();

// WebSocket 连接实例
let ws = null;
let wsReconnectAttempts = 0;
let wsIsReconnecting = false; // 标识是否正在重连
const wsMaxReconnectAttempts = 5;
const wsReconnectDelay = 3000;

// 全局变量，方便在控制台查看
window.__DATA_FEED_CONFIG__ = null;

// 图表API引用（用于重连时调用 resetCache/resetData）
let chartApi = null;

/**
 * 设置图表API引用（供 useTradingView 调用）
 * @param {Object} chartWidget - TradingView widget 实例
 */
export function setChartApi(chartWidget) {
    chartApi = chartWidget;
}

/**
 * 重置图表数据（供外部调用或重连时自动调用）
 * 在 WebSocket 重连成功后，需要调用此方法让图表重新请求数据
 */
function resetChartData() {
    if (chartApi) {
        try {
            // 调用 resetCache 清除所有缓存的K线数据
            chartApi.resetCache();
            // 调用 resetData 让库重新调用 getBars 重新请求数据
            const activeChart = chartApi.activeChart();
            if (activeChart) {
                activeChart.resetData();
                console.log('📊 图表数据已重置，准备重新订阅');
            }
        } catch (error) {
            console.warn('⚠️ 重置图表数据失败:', error.message);
        }
    }
}

/**
 * 重新订阅所有K线数据
 */
function resubscribeAllBars() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.warn('⚠️ WebSocket 未连接，无法重新订阅K线');
        return;
    }

    // 遍历所有活跃的订阅，重新发送订阅消息
    subscriptions.forEach((subscription, subscriberUID) => {
        const subscribeMessage = {
            protocolVersion: "2.0",
            type: "SUBSCRIBE",
            requestId: generateRequestId(),
            timestamp: Date.now(),
            data: {
                subscriptions: [subscription.subscriptionKey]
            }
        };
        console.log('📈 重新订阅K线:', subscription.subscriptionKey);
        ws.send(JSON.stringify(subscribeMessage));
    });

    console.log(`✅ 完成K线重新订阅，共 ${subscriptions.size} 个订阅`);
}

/**
 * 重新订阅所有报价数据
 */
function resubscribeAllQuotes() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.warn('⚠️ WebSocket 未连接，无法重新订阅报价');
        return;
    }

    // 遍历所有活跃的报价订阅，重新发送订阅消息
    const newSubscriptions = [];
    quotesSubscriptions.forEach((subscription, listenerGUID) => {
        subscription.symbols.forEach(symbol => {
            const formattedSymbol = formatSymbol(symbol);
            const subscriptionKey = buildSubscriptionKey(
                formattedSymbol.split(':')[0],
                formattedSymbol.split(':')[1],
                DataType.QUOTES
            );
            if (!newSubscriptions.includes(subscriptionKey)) {
                newSubscriptions.push(subscriptionKey);
            }
        });
    });

    if (newSubscriptions.length > 0) {
        const subscribeMessage = {
            protocolVersion: "2.0",
            type: "SUBSCRIBE",
            requestId: generateRequestId(),
            timestamp: Date.now(),
            data: {
                subscriptions: newSubscriptions
            }
        };
        console.log('📊 重新订阅报价:', newSubscriptions);
        ws.send(JSON.stringify(subscribeMessage));
    }

    console.log(`✅ 完成报价重新订阅，共 ${newSubscriptions.length} 个订阅`);
}

/**
 * 格式化交易符号，确保使用 EXCHANGE:SYMBOL 格式
 * @param {string} symbol - 交易符号
 * @param {string} defaultExchange - 默认交易所（默认：BINANCE）
 * @returns {string} 格式化后的符号
 */
function formatSymbol(symbol, defaultExchange = 'BINANCE') {
    if (!symbol) {
        return symbol;
    }
    if (symbol.includes(':')) {
        return symbol; // 已有交易所前缀
    }
    return `${defaultExchange}:${symbol}`;
}


/**
 * 建立 WebSocket 连接
 * @param {boolean} isManualReconnect - 是否是手动重连（重置计数器）
 */
function connectWebSocket(isManualReconnect = false) {
    // 如果是手动重连，重置计数器
    if (isManualReconnect) {
        wsReconnectAttempts = 0;
    }

    // 检查是否正在重连（通过单独变量标识，而不是依赖计数器）
    const wasReconnecting = wsIsReconnecting;

    if (ws && ws.readyState === WebSocket.OPEN) {
        return Promise.resolve();
    }

    if (ws && ws.readyState === WebSocket.CONNECTING) {
        return new Promise((resolve, reject) => {
            ws.addEventListener('open', () => resolve());
            ws.addEventListener('error', (error) => reject(error));
        });
    }

    return new Promise((resolve, reject) => {
        // 直接连接到后端 WebSocket 服务（绕过 Vite 代理问题）
        const wsUrl = 'ws://127.0.0.1:8000/ws/market';
        ws = new WebSocket(wsUrl);

        const timeout = setTimeout(() => {
            ws.close();
            reject(new Error('WebSocket connection timeout'));
        }, 5000);

        ws.onopen = () => {
            clearTimeout(timeout);
            // 使用单独的 wsIsReconnecting 变量，而不是依赖 wsReconnectAttempts
            const wasReconnecting = wsIsReconnecting;
            wsIsReconnecting = false; // 重置重连状态
            wsReconnectAttempts = 0;

            console.log(`✅ WebSocket 连接已建立${wasReconnecting ? '（重连成功）' : ''}`);

            // 无论是首次连接还是重连，都需要处理待处理的请求队列
            processPendingRequestsQueue();

            // 如果是重连，触发图表数据重置和重新订阅
            if (wasReconnecting) {

                // 重置图表数据（清除缓存并触发重新请求）
                setTimeout(() => {
                    resetChartData();
                }, 200); // 200ms 延迟确保图表完全就绪

                // 重新订阅K线和报价数据
                // 注意：quotesSubscriptions 可能为空（因为清空了），
                // 但 TradingView 会自动重新调用 subscribeQuotes
                setTimeout(() => {
                    resubscribeAllBars();
                    resubscribeAllQuotes();
                }, 300); // 300ms 延迟，确保 resetData 先完成
            }
        };

        ws.onerror = (error) => {
            clearTimeout(timeout);
            reject(error);
        };

        ws.onclose = (event) => {
            // 标记连接已断开，阻止发送更多消息
            ws = null;

            // 检查是否有任何活跃订阅（包括 k线和 quotes）
            const hasActiveSubscriptions = subscriptions.size > 0 || quotesSubscriptions.size > 0;

            // 只有在有活跃订阅且未达到最大重连次数时才尝试重连
            if (wsReconnectAttempts < wsMaxReconnectAttempts && hasActiveSubscriptions) {
                wsReconnectAttempts++;
                wsIsReconnecting = true; // 标记正在重连
                console.log(`🔄 尝试第 ${wsReconnectAttempts} 次重连（${wsMaxReconnectAttempts} 次最大）...`);

                setTimeout(() => {
                    // 传入 true 表示这是重连调用，会自动重置计数器
                    connectWebSocket(true)
                        .then(() => {
                            // 重连成功 - onopen 中的逻辑会自动处理重置和重新订阅
                            console.log('✅ 重连成功，数据正在恢复中...');
                        })
                        .catch((error) => {
                            console.warn(`⚠️ 重连失败: ${error.message}`);
                        });
                }, wsReconnectDelay);
            } else if (wsReconnectAttempts >= wsMaxReconnectAttempts) {
                console.warn('❌ 已达到最大重连次数，停止自动重连');
                wsReconnectAttempts = wsMaxReconnectAttempts; // 确保不再增加
            }

            // 清理所有挂起的请求
            if (pendingRequests.size > 0) {
                pendingRequests.forEach((request, requestId) => {
                    // 清理超时定时器
                    if (request.timeoutId) {
                        clearTimeout(request.timeoutId);
                    }
                    // 通知 resultCallback
                    if (request.resultCallback) {
                        request.resultCallback({
                            action: 'error',
                            type: request.type,
                            requestId: requestId,
                            error: { code: 'CONNECTION_CLOSED', message: 'Connection closed' }
                        });
                    }
                });
                pendingRequests.clear();
            }

            // 注意：不清理 subscriptions、quotesSubscriptions 和 subscribedQuotes
            // 因为重连后需要利用这些信息重新订阅
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (error) {
                // 静默处理消息解析错误
            }
        };
    });
}

/**
 * 处理WebSocket消息（支持v2.0协议三阶段模式）
 * @param {Object} data - WebSocket消息数据
 */
function handleWebSocketMessage(data) {
    const { type, requestId, data: messageData } = data;

    // v2.0 协议: 使用 type 字段替代 action 字段
    // 根据 type 分发处理
    switch (type) {
        case 'ACK':
            // 阶段1：确认收到请求
            handleAck(requestId, messageData);
            break;

        case 'CONFIG_DATA':
        case 'SEARCH_SYMBOLS_DATA':
        case 'SYMBOL_DATA':
        case 'KLINES_DATA':
        case 'QUOTES_DATA':
        case 'SUBSCRIPTION_DATA':
            // 阶段2：请求成功完成 - v2.0 使用具体数据类型
            handleSuccess(requestId, messageData, type);
            break;

        case 'ERROR':
            // 阶段2：请求失败
            handleError(requestId, messageData);
            break;

        case 'UPDATE':
            // 阶段3：实时数据推送
            // v2.0: 传入完整 data 对象（包含 subscriptionKey）
            handleUpdate(data);
            break;

        default:
            console.warn(`⚠️ 未知 WebSocket 消息类型: ${type}`, data);
    }
}



/**
 * 获取默认配置
 */
function getDefaultConfig() {
    return {
        supports_search: true,
        supports_group_request: true,  // 启用批量请求，支持 watchlist
        supported_resolutions: ['1', '5', '15', '60', '1D', '1W', '1M'],
        intraday_multipliers: ['1', '5', '15', '60'],
        symbols_types: [
            { name: 'All types', value: '' },
            { name: 'Stock', value: 'stock' },
            { name: 'Crypto', value: 'crypto' },
            { name: 'Forex', value: 'forex' },
            { name: 'Index', value: 'index' },
            { name: 'Future', value: 'future' }
        ]
    };
}

/**
 * 获取数据源配置
 * @param {Function} callback - 回调函数，接收配置对象
 */
function getConfiguration(callback) {
    if (datafeedConfiguration) {
        callback(datafeedConfiguration);
        return;
    }

    // 使用WebSocket GET请求获取配置
    sendWSRequest({ type: "config" }, (response) => {
        // v2.0 协议: 使用 type === 'CONFIG_DATA' 而非 action === 'success'
        if (response.type === 'CONFIG_DATA') {
            datafeedConfiguration = response.data;
            // 强制启用批量请求支持（Watchlist 需要此功能）
            datafeedConfiguration.supports_group_request = true;
            callback(datafeedConfiguration);
        } else if (response.type === 'ERROR') {
            datafeedConfiguration = getDefaultConfig();
            callback(datafeedConfiguration);
        }
    });
}

export default {
    /**
     * TradingView调用此方法获取数据源配置
     * @param {Function} callback - 回调函数，接收DatafeedConfiguration对象
     */
    onReady: (callback) => {
        getConfiguration((config) => {
            setTimeout(() => callback(config), 0);
        });
    },

    /**
     * 搜索交易标的
     * @param {string} userInput - 用户输入的搜索关键词
     * @param {string} exchange - 交易所代码（可选）
     * @param {string} symbolType - 标的类型（可选）
     * @param {Function} onResultReadyCallback - 回调函数，返回搜索结果数组
     */
    searchSymbols: (userInput, exchange, symbolType, onResultReadyCallback) => {
        // 使用WebSocket GET请求搜索交易对
        sendWSRequest({
            type: "search_symbols",
            query: userInput,
            exchange: exchange || "BINANCE",
            limit: 50
        }, (response) => {
            // v2.0 协议: 使用 type === 'SEARCH_SYMBOLS_DATA'
            if (response.type === 'SEARCH_SYMBOLS_DATA') {
                const tvSymbols = response.data.symbols.map(item => {
                    // ticker: 交易代码（不带交易所前缀），如 BTCUSDT
                    // symbol: 标的全名（带交易所前缀），如 BINANCE:BTCUSDT
                    const ticker = item.ticker || (item.symbol.includes(':') ? item.symbol.split(':')[1] : item.symbol);
                    const symbol = item.symbol.includes(':') ? item.symbol : `${item.exchange || 'BINANCE'}:${item.ticker || item.symbol}`;

                    return {
                        symbol: symbol,
                        full_name: item.full_name || symbol,
                        description: item.description || ticker,
                        exchange: item.exchange,
                        ticker: ticker,
                        type: item.type
                    };
                });
                onResultReadyCallback(tvSymbols);
            } else if (response.type === 'ERROR') {
                onResultReadyCallback([]);
            }
        });
    },

    /**
     * 解析标的详情
     * @param {string} symbolName - 标的名称（包含交易所）
     * @param {Function} onSymbolResolvedCallback - 解析成功回调
     * @param {Function} onResolveErrorCallback - 解析失败回调
     * @param {Object} extension - 扩展参数（可选）
     */
    resolveSymbol: (symbolName, onSymbolResolvedCallback, onResolveErrorCallback) => {
        // 使用公共格式化函数
        const formattedSymbol = formatSymbol(symbolName);

        // 使用WebSocket GET请求获取交易对详情
        sendWSRequest({
            type: "resolve_symbol",
            symbol: formattedSymbol
        }, (response) => {
            // v2.0 协议: 使用 type === 'SYMBOL_DATA'
            if (response.type === 'SYMBOL_DATA') {
                const data = response.data;

                // 根据设计文档，name 应该是交易代码（不带交易所前缀），如 BTCUSDT
                // ticker 应该是标的全名（带交易所前缀），如 BINANCE:BTCUSDT
                const name = data.name || (formattedSymbol.includes(':') ? formattedSymbol.split(':')[1] : formattedSymbol);
                const ticker = formattedSymbol;  // 保持 EXCHANGE:SYMBOL 格式

                const symbolInfo = {
                    // name: 交易代码（显示在左上角），如 BTCUSDT
                    name: name,
                    // ticker: 标的全名（用于 API 请求），如 BINANCE:BTCUSDT
                    ticker: ticker,
                    description: data.description || name,
                    type: data.type || 'crypto',
                    session: data.session || '24x7',
                    exchange: data.exchange || (formattedSymbol.includes(':') ? formattedSymbol.split(':')[0] : 'BINANCE'),
                    listed_exchange: data.listed_exchange || data.exchange || (formattedSymbol.includes(':') ? formattedSymbol.split(':')[0] : 'BINANCE'),
                    timezone: data.timezone || 'Etc/UTC',
                    minmov: data.minmov || 1,
                    pricescale: data.pricescale || 100,
                    has_intraday: data.has_intraday !== false,
                    has_daily: data.has_daily !== false,
                    has_weekly_and_monthly: data.has_weekly_and_monthly !== false,
                    visible_plots_set: data.visible_plots_set || 'ohlcv',
                    supported_resolutions: data.supported_resolutions || ['1', '5', '15', '60', '240', '1D', '1W', '1M'],
                    volume_precision: data.volume_precision || 0,
                    data_status: data.data_status || 'streaming'
                };

                onSymbolResolvedCallback(symbolInfo);
            } else if (response.type === 'ERROR') {
                onResolveErrorCallback(response.error?.message || 'Symbol resolution failed');
            } else {
                // 处理类型不匹配的情况 - 调用错误回调
                onResolveErrorCallback(`Unexpected response type: ${response.type || 'unknown'}`);
            }
        });
    },

    /**
     * 获取K线历史数据
     * @param {Object} symbolInfo - 标的信息对象
     * @param {string} resolution - 时间周期（1, 5, 15, 60, 240, 1D, 1W, 1M）
     * @param {Object} periodParams - 时间范围参数
     * @param {Function} onHistoryCallback - 成功回调
     * @param {Function} onErrorCallback - 错误回调
     */
    getBars: (symbolInfo, resolution, periodParams, onHistoryCallback, onErrorCallback) => {
        // 使用 ticker (EXCHANGE:SYMBOL 格式) 进行 API 请求
        const symbol = symbolInfo.ticker || symbolInfo.name;
        const countBack = periodParams.countBack || 300;

        const resolutionMs = resolutionToMs(resolution);
        const extendMs = 50 * resolutionMs;

        const originalFrom = periodParams.from * 1000;
        const from_ts = originalFrom - extendMs;
        const to_ts = periodParams.to * 1000;

        // 使用WebSocket GET请求获取K线数据
        // interval 与数据库字段和后端API保持一致（设计文档 v2.1 规范）
        sendWSRequest({
            type: "klines",
            symbol: symbol,
            interval: resolution,  // 使用 interval 而非 resolution
            from_time: from_ts,
            to_time: to_ts
        }, (response) => {
            // v2.0 协议: 使用 type === 'KLINES_DATA'
            if (response.type === 'KLINES_DATA') {
                let bars = response.data.bars.map(bar => ({
                    time: bar.time,
                    open: bar.open,
                    high: bar.high,
                    low: bar.low,
                    close: bar.close,
                    volume: bar.volume
                }));

                bars = bars.filter(bar => bar.time <= to_ts);

                if (bars.length > countBack) {
                    bars = bars.slice(-countBack);
                }

                const meta = {
                    noData: response.data.noData || bars.length === 0,
                    nextTime: response.data.nextTime || null
                };

                onHistoryCallback(bars, meta);
            } else if (response.type === 'ERROR') {
                onErrorCallback(response.error?.message || 'Failed to load bars');
            }
        });
    },

    subscribeBars: (symbolInfo, resolution, onRealtimeCallback, subscriberUID, onResetCacheNeededCallback) => {
        // 构建 v2.0 格式的订阅键
        const subscriptionKey = buildKeyFromSymbolInfo(symbolInfo, DataType.KLINE, resolution);

        const subscriptionInfo = {
            subscriberUID,
            symbolInfo,
            resolution,
            onRealtimeCallback,
            onResetCacheNeededCallback,
            subscriptionKey,
            timestamp: Date.now()
        };

        subscriptions.set(subscriberUID, subscriptionInfo);

        connectWebSocket()
            .then(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    const subscribeMessage = {
                        protocolVersion: "2.0",
                        type: "SUBSCRIBE",
                        requestId: generateRequestId(),
                        timestamp: Date.now(),
                        data: {
                            subscriptions: [subscriptionKey]
                        }
                    };
                    ws.send(JSON.stringify(subscribeMessage));
                }
            })
            .catch(() => {
                // 静默处理 WebSocket 连接失败
            });
    },

    unsubscribeBars: (subscriberUID) => {
        console.log('🔥 unsubscribeBars 被调用:', {
            subscriberUID,
            timestamp: new Date().toISOString(),
            stack: new Error().stack
        });

        const subscriptionInfo = subscriptions.get(subscriberUID);
        if (!subscriptionInfo) {
            console.log('⚠️  unsubscribeBars: 未找到 subscriberUID 对应的订阅信息');
            return;
        }

        console.log('📊 unsubscribeBars 订阅信息:', {
            subscriptionKey: subscriptionInfo.subscriptionKey,
            resolution: subscriptionInfo.resolution,
            activeBarsSubscriptions: Array.from(subscriptions.keys())
        });

        // 使用存储的 v2.0 订阅键
        const klineSubscription = subscriptionInfo.subscriptionKey;
        console.log('🗑️  准备取消 K 线订阅:', klineSubscription);

        // 直接发送取消订阅请求
        if (ws && ws.readyState === WebSocket.OPEN) {
            const unsubscribeMessage = {
                protocolVersion: "2.0",
                type: "UNSUBSCRIBE",
                requestId: generateRequestId(),
                timestamp: Date.now(),
                data: {
                    subscriptions: [klineSubscription]
                }
            };
            console.log('📤 发送取消 K 线订阅 WebSocket 消息:', unsubscribeMessage);
            ws.send(JSON.stringify(unsubscribeMessage));
        } else {
            console.log('⚠️  WebSocket 未连接，跳过取消 K 线订阅消息发送');
        }

        subscriptions.delete(subscriberUID);
        console.log('✅ 清理本地 K 线订阅记录完成，剩余订阅:', Array.from(subscriptions.keys()));
    },

    /**
     * 获取报价数据（TradingView Quotes API）- v2.0 规范
     * @param {string[]} symbols - 标的数组，格式：EXCHANGE:SYMBOL
     * @param {Function} onDataCallback - 数据回调
     * @param {Function} onErrorCallback - 错误回调
     */
    getQuotes: (symbols, onDataCallback, onErrorCallback) => {
        // 处理空symbols数组 - 直接返回空数组
        if (!symbols || symbols.length === 0) {
            onDataCallback([]);
            return;
        }

        // 确保所有symbols都使用EXCHANGE:SYMBOL格式
        const formattedSymbols = symbols.map(symbol => formatSymbol(symbol));

        // 使用WebSocket GET请求获取报价数据
        sendWSRequest({
            type: "quotes",
            symbols: formattedSymbols
        }, (response) => {
            // v2.0 协议: 使用 type === 'QUOTES_DATA'
            if (response.type === 'QUOTES_DATA') {
                const quotes = response.data.quotes.map((item) => {
                    return item;
                });

                onDataCallback(quotes);
            } else if (response.type === 'ERROR') {
                const errorMsg = response.error?.message || 'Failed to get quotes';
                onErrorCallback(errorMsg);
            }
        });
    },


    /**
     * 取消订阅实时报价数据（TradingView Quotes API）- v2.0 规范
     * @param {string} listenerGUID - 唯一标识符
     */
    unsubscribeQuotes: (listenerGUID) => {
        const subscriptionInfo = quotesSubscriptions.get(listenerGUID);
        if (!subscriptionInfo) {
            return;
        }

        // 🔧 修复：检查引用计数，只在最后一个引用时才取消 WebSocket 订阅
        const subscriptionsToRemove = [];

        subscriptionInfo.symbols.forEach(symbol => {
            const formattedSymbol = formatSymbol(symbol);
            // 使用 buildSubscriptionKey 构建 v2.0 格式的订阅键
            const subscriptionKey = buildSubscriptionKey(
                formattedSymbol.split(':')[0],
                formattedSymbol.split(':')[1],
                DataType.QUOTES
            );

            if (subscribedQuotes.has(subscriptionKey)) {
                const count = subscribedQuotes.get(subscriptionKey);
                if (count > 1) {
                    // 还有其他引用，只递减计数，不发送取消订阅
                    subscribedQuotes.set(subscriptionKey, count - 1);
                } else {
                    // 最后一个引用，需要发送取消订阅消息
                    subscriptionsToRemove.push(subscriptionKey);
                    subscribedQuotes.delete(subscriptionKey);
                }
            }
        });

        // 只有当需要真正取消时才发送WebSocket消息
        if (subscriptionsToRemove.length > 0) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                const unsubscribeMessage = {
                    protocolVersion: "2.0",
                    type: "UNSUBSCRIBE",
                    requestId: generateRequestId(),
                    timestamp: Date.now(),
                    data: {
                        subscriptions: subscriptionsToRemove
                    }
                };
                ws.send(JSON.stringify(unsubscribeMessage));
            }
        }

        // 清理订阅记录
        quotesSubscriptions.delete(listenerGUID);
    },

    /**
     * 获取报价数据（TradingView Quotes API）- v2.0 规范
     * @param {string[]} symbols - 标的数组，格式：EXCHANGE:SYMBOL
     * @param {string[]} fastSymbols - 快速标的数组，格式：EXCHANGE:SYMBOL
     * @param {Function} onRealtimeCallback - 实时数据回调函数
     * @param {string} listenerGUID - 唯一标识符
     */
    subscribeQuotes: (symbols, fastSymbols, onRealtimeCallback, listenerGUID) => {
        // 合并 symbols 和 fastSymbols，并去重
        const allSymbols = [...new Set([...symbols, ...fastSymbols])];

        // 如果已存在相同 listenerGUID，先取消旧订阅（避免重复）
        if (quotesSubscriptions.has(listenerGUID)) {
            this.unsubscribeQuotes(listenerGUID);
        }

        // 存储订阅信息 - 使用构建后的订阅键格式以便匹配后端推送
        const storedSymbols = allSymbols.map(s => {
            const formattedSymbol = formatSymbol(s);
            return buildSubscriptionKey(
                formattedSymbol.split(':')[0],
                formattedSymbol.split(':')[1],
                DataType.QUOTES
            ).replace('@QUOTES', '');  // 去掉 @QUOTES 后缀
        });
        quotesSubscriptions.set(listenerGUID, {
            symbols: storedSymbols,
            onRealtimeCallback
        });

        // 🔧 修复：更新引用计数并找出真正需要发送的新订阅
        const newSubscriptions = [];
        allSymbols.forEach(symbol => {
            // 使用 formatSymbol 确保格式正确
            const formattedSymbol = formatSymbol(symbol);
            // 使用 buildSubscriptionKey 构建 v2.0 格式的订阅键
            const subscriptionKey = buildSubscriptionKey(
                formattedSymbol.split(':')[0],
                formattedSymbol.split(':')[1],
                DataType.QUOTES
            );

            if (!subscribedQuotes.has(subscriptionKey)) {
                // 新的订阅，需要发送
                newSubscriptions.push(subscriptionKey);
                subscribedQuotes.set(subscriptionKey, 1);
            } else {
                // 已存在，增加引用计数
                const newCount = subscribedQuotes.get(subscriptionKey) + 1;
                subscribedQuotes.set(subscriptionKey, newCount);
            }
        });

        // 只有当有新订阅时才发送WebSocket消息
        if (newSubscriptions.length > 0) {
            connectWebSocket()
                .then(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        const subscribeMessage = {
                            protocolVersion: "2.0",
                            type: "SUBSCRIBE",
                            requestId: generateRequestId(),
                            timestamp: Date.now(),
                            data: {
                                subscriptions: newSubscriptions
                            }
                        };
                        ws.send(JSON.stringify(subscribeMessage));
                    }
                });
        }
    },

    /**
     * 设置图表API引用（用于重连时调用 resetCache/resetData）
     * @param {Object} chartWidget - TradingView widget 实例
     */
    setChartApi: (chartWidget) => {
        setChartApi(chartWidget);
    }

};
