// ========================================
// v2.0 订阅键格式管理
// 格式: {EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{INTERVAL}]
// 示例:
//   - BINANCE:BTCUSDT@KLINE_1      - 1分钟K线
//   - BINANCE:BTCUSDT@KLINE_60    - 1小时K线
//   - BINANCE:BTCUSDT@QUOTES      - 报价数据
//   - BINANCE:BTCUSDT@TRADE       - 实时交易
//   - BINANCE:BTCUSDT.PERP@KLINE_1 - 永续合约K线
//   - BINANCE:SPOT@ACCOUNT        - 现货账户信息
//   - BINANCE:FUTURES@ACCOUNT     - 期货账户信息
// ========================================

// Import DataService for unified data access
import { dataService } from '../../../services/data-service/DataService'

const DataType = {
    KLINE: 'KLINE',
    QUOTES: 'QUOTES',
    TRADE: 'TRADE',
    ACCOUNT: 'ACCOUNT'
};

/**
 * 构建 v2.0 格式的订阅键
 * @param {string} exchange - 交易所代码（如 BINANCE）
 * @param {string} symbol - 交易符号（如 BTCUSDT 或 BTCUSDT.PERP），账户类型用 SPOT@ACCOUNT 或 FUTURES@ACCOUNT
 * @param {string} dataType - 数据类型（KLINE, QUOTES, TRADE, ACCOUNT）
 * @param {string} [interval] - K线周期（可选，如 '1', '60'）
 * @returns {string} v2.0 格式的订阅键
 */
function buildSubscriptionKey(exchange, symbol, dataType, interval = null) {
    // 账户类型订阅键格式: BINANCE:SPOT@ACCOUNT 或 BINANCE:FUTURES@ACCOUNT
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
// 统一通过 DataService 处理请求和订阅
// ========================================

/**
 * 发送WebSocket请求（通过 DataService）
 * @param {Object} data - 请求数据（包含type字段）
 * @param {Function} resultCallback - 结果回调函数
 * @param {Function} ackCallback - ACK回调函数（可选，暂不支持）
 * @param {Number} timeout - 超时时间（默认10000ms，暂不支持）
 */
function sendWSRequest(data, resultCallback, ackCallback = null, timeout = 10000) {
    // 映射请求类型
    const typeMap = {
        'config': 'GET_CONFIG',
        'search_symbols': 'GET_SEARCH_SYMBOLS',
        'resolve_symbol': 'GET_RESOLVE_SYMBOL',
        'klines': 'GET_KLINES',
        'quotes': 'GET_QUOTES',
        'server_time': 'GET_SERVER_TIME',
    };

    const requestType = typeMap[data.type] || data.type;

    // 使用 DataService 发送请求
    dataService.request(requestType, data)
        .then((response) => {
            // 转换为与原生 WebSocket 相同的格式
            const responseTypeMap = {
                'GET_CONFIG': 'CONFIG_DATA',
                'GET_SEARCH_SYMBOLS': 'SEARCH_SYMBOLS_DATA',
                'GET_RESOLVE_SYMBOL': 'SYMBOL_DATA',
            };
            resultCallback({
                type: responseTypeMap[requestType] || requestType + '_DATA',
                data: response
            });
        })
        .catch((error) => {
            resultCallback({
                type: 'ERROR',
                error: { code: 'REQUEST_FAILED', message: error.message }
            });
        });
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

    // 使用 DataService.getConfig 获取配置
    dataService.getConfig()
        .then((config) => {
            datafeedConfiguration = config;
            callback(datafeedConfiguration);
        })
        .catch((error) => {
            console.warn('获取图表配置失败，使用默认配置:', error.message);
            datafeedConfiguration = getDefaultConfig();
            callback(datafeedConfiguration);
        });
}

// ========================================
// 模块初始化：连接 DataService
// ========================================
// 当模块加载时自动连接 DataService
// DataService 会自动处理重连逻辑
dataService.connect().catch((error) => {
    console.error('DataService 连接失败:', error.message);
});

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
        console.log('[DataFeed] resolveSymbol:', formattedSymbol);

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

        // 使用 DataService 获取K线数据 (替换原生 WebSocket)
        // interval 与数据库字段和后端API保持一致（设计文档 v2.1 规范）
        // 使用 camelCase 格式 (fromTime, toTime)，后端使用 SnakeCaseModel 自动转换
        dataService.getKlines({
            symbol: symbol,
            interval: resolution,  // 使用 interval 而非 resolution
            fromTime: from_ts,
            toTime: to_ts,
            limit: countBack
        }).then((response) => {
            // DataService 返回格式: { bars: [], noData, nextTime }
            let bars = response.bars.map(bar => ({
                time: bar.time,
                open: bar.open,
                high: bar.high,
                low: bar.low,
                close: bar.close,
                volume: bar.volume
            }));

            // 过滤超出请求范围的K线
            bars = bars.filter(bar => bar.time <= to_ts);

            // 限制返回数量
            if (bars.length > countBack) {
                bars = bars.slice(-countBack);
            }

            const meta = {
                noData: response.noData || bars.length === 0,
                nextTime: response.nextTime || null
            };

            onHistoryCallback(bars, meta);
        }).catch((error) => {
            onErrorCallback(error?.message || 'Failed to load bars');
        });
    },

    subscribeBars: (symbolInfo, resolution, onRealtimeCallback, subscriberUID, onResetCacheNeededCallback) => {
        // 构建 v2.0 格式的订阅键
        const subscriptionKey = buildKeyFromSymbolInfo(symbolInfo, DataType.KLINE, resolution);

        // 解析 symbol 和 interval
        const ticker = symbolInfo.ticker || symbolInfo.name || '';
        const [exchange, ...symbolParts] = ticker.split(':');
        const symbol = symbolParts.join(':') || symbolParts[0];

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

        // 使用 DataService.subscribeKline 替换原生 WebSocket 订阅
        // DataService 会自动处理连接和重连
        const unsubscribe = dataService.subscribeKline(
            `${exchange}:${symbol}`,
            resolution,
            (bar, sk) => {
                // 将 K线数据转换为 TradingView 格式并回调
                onRealtimeCallback(bar);
            }
        );

        // 存储取消订阅函数，以便后续调用
        subscriptionInfo.unsubscribe = unsubscribe;
    },

    unsubscribeBars: (subscriberUID) => {
        console.log('unsubscribeBars 被调用:', {
            subscriberUID,
            timestamp: new Date().toISOString(),
        });

        const subscriptionInfo = subscriptions.get(subscriberUID);
        if (!subscriptionInfo) {
            console.log('unsubscribeBars: 未找到 subscriberUID 对应的订阅信息');
            return;
        }

        console.log('📊 unsubscribeBars 订阅信息:', {
            subscriptionKey: subscriptionInfo.subscriptionKey,
            resolution: subscriptionInfo.resolution,
            activeBarsSubscriptions: Array.from(subscriptions.keys())
        });

        // 使用存储的 v2.0 订阅键
        const klineSubscription = subscriptionInfo.subscriptionKey;
        console.log('准备取消 K 线订阅:', klineSubscription);

        // 使用 DataService.unsubscribe 替换原生 WebSocket 取消订阅
        if (subscriptionInfo.unsubscribe) {
            // 调用 DataService 返回的取消订阅函数
            subscriptionInfo.unsubscribe();
        } else {
            // 如果没有存储的取消订阅函数，直接调用 dataService.unsubscribe
            dataService.unsubscribe(klineSubscription);
        }

        subscriptions.delete(subscriberUID);
        console.log('清理本地 K 线订阅记录完成，剩余订阅:', Array.from(subscriptions.keys()));
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

        // 使用 DataService.getQuotes 替换原生 WebSocket 请求
        dataService.getQuotes(formattedSymbols)
            .then((response) => {
                // DataService 返回格式: { quotes: [] }
                const quotes = response.quotes || [];
                onDataCallback(quotes);
            })
            .catch((error) => {
                const errorMsg = error?.message || 'Failed to get quotes';
                onErrorCallback(errorMsg);
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

        // 使用 DataService.unsubscribe 替换原生 WebSocket 取消订阅
        // 注意：DataService 内部处理引用计数
        if (subscriptionInfo.unsubscribe) {
            subscriptionInfo.unsubscribe();
        }

        // 清理本地订阅记录
        quotesSubscriptions.delete(listenerGUID);
    },

    /**
     * 获取报价数据（TradingView Quotes API）- v2.0 规范
     * @param {string[]} symbols - 标的数组，格式：EXCHANGE:SYMBOL
     * @param {string[]} fastSymbols - 快速标的数组，格式：EXCHANGE:SYMBOL
     * @param {Function} onRealtimeCallback - 实时数据回调函数
     * @param {string} listenerGUID - 唯一标识符
     */
    subscribeQuotes(symbols, fastSymbols, onRealtimeCallback, listenerGUID) {
        // 合并 symbols 和 fastSymbols，并去重
        const allSymbols = [...new Set([...symbols, ...fastSymbols])];

        // 如果已存在相同 listenerGUID，直接返回已存储的取消订阅函数（不重复订阅）
        if (quotesSubscriptions.has(listenerGUID)) {
            const existing = quotesSubscriptions.get(listenerGUID);
            return existing.unsubscribe;
        }

        // 直接使用完整格式 EXCHANGE:SYMBOL（如 BINANCE:BTCUSDT）
        // 无需去掉交易所前缀，后端需要完整格式进行订阅匹配
        const formattedSymbols = allSymbols.map(symbol => formatSymbol(symbol));

        // 使用 DataService.subscribeQuotes 替换原生 WebSocket 订阅
        const unsubscribe = dataService.subscribeQuotes(
            formattedSymbols,
            (quotesMap) => {
                // DataService 返回 Map 格式，转换为 TradingView 期望的数组格式
                // 修复：将 payload 包装成数组格式，以匹配 getQuotes 的数据格式
                const quoteDataArray = Array.from(quotesMap.values());
                onRealtimeCallback(quoteDataArray);
            }
        );

        // 存储订阅信息
        quotesSubscriptions.set(listenerGUID, {
            symbols: formattedSymbols,
            onRealtimeCallback,
            unsubscribe  // 存储取消订阅函数
        });

        // 返回取消订阅函数给 TradingView
        return unsubscribe;
    },

    /**
     * 设置图表API引用（用于重连时调用 resetCache/resetData）
     * @param {Object} chartWidget - TradingView widget 实例
     */
    setChartApi: (chartWidget) => {
        setChartApi(chartWidget);
    },

    /**
     * 调试函数：获取订阅状态
     * 在浏览器控制台调用 window.datafeed.getSubscriptionStatus() 查看
     * @returns {Object} 订阅状态信息
     */
    getSubscriptionStatus: () => {
        const status = {
            barsSubscriptions: Array.from(subscriptions.keys()),
            quotesSubscriptions: Array.from(quotesSubscriptions.keys()),
            dataServiceConnected: dataService.isConnected,
        };
        console.log('📋 订阅状态:', status);
        return status;
    },

    /**
     * 调试函数：检查 DataService 连接状态
     * 在浏览器控制台调用 window.datafeed.getConnectionStatus() 使用
     * @returns {Object} 连接状态信息
     */
    getConnectionStatus: () => {
        const status = {
            isConnected: dataService.isConnected,
        };
        console.log('🔌 连接状态:', status);
        return status;
    }

};
