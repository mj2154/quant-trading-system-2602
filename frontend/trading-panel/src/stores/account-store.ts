/**
 * 账户信息状态管理 Store
 *
 * 管理账户信息查询、WebSocket通信和实时更新
 *
 * 使用 WebSocket 协议 (protocolVersion 2.0) 与后端通信
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  SpotAccountInfo,
  FuturesAccountInfo,
  AccountResponse,
  AccountOverview,
  PositionItem,
  BalanceItem,
} from '../types/account-types'

// WebSocket URL - 使用环境变量或默认配置
const WS_BASE_URL = import.meta.env?.VITE_WS_URL || 'ws://127.0.0.1:8000'

// ==================== 常量定义 ====================

/**
 * requestId 生成器
 */
let requestIdCounter = 0
function generateRequestId(prefix: string = 'req'): string {
  const timestamp = Date.now()
  requestIdCounter = (requestIdCounter + 1) % 10000
  return `${prefix}_${timestamp}_${requestIdCounter}`
}

// ==================== Store 定义 ====================

export const useAccountStore = defineStore('account', () => {
  // ==================== 状态 ====================

  // 现货账户信息
  const spotAccount = ref<SpotAccountInfo | null>(null)
  const spotLoading = ref(false)
  const spotError = ref<string | null>(null)

  // 期货账户信息
  const futuresAccount = ref<FuturesAccountInfo | null>(null)
  const futuresLoading = ref(false)
  const futuresError = ref<string | null>(null)

  // WebSocket 连接
  const ws = ref<WebSocket | null>(null)
  const wsConnected = ref(false)
  const wsConnecting = ref(false)

  // 待处理的请求回调
  const pendingRequests = new Map<string, {
    resolve: (value: unknown) => void
    reject: (reason?: unknown) => void
    timeoutId: number
  }>()

  // WebSocket 重连定时器引用（用于清理）
  let reconnectTimeoutId: number | null = null

  // 请求超时时间 (毫秒)
  const REQUEST_TIMEOUT = 30000

  // ==================== 计算属性 ====================

  /**
   * 现货账户概览
   *
   * 注意：totalUSDT 计算为简化实现，仅统计 USDT 余额。
   * 完整实现需要获取各币种对 USDT 的实时价格进行换算。
   */
  const spotOverview = computed((): AccountOverview | null => {
    if (!spotAccount.value) return null

    const balances = spotAccount.value.balances || []
    // 计算总资产（简化计算：仅统计 USDT 余额）
    // 完整实现需要获取各币种实时价格进行换算
    const usdtBalance = balances.find(b => b.asset === 'USDT')
    const totalUSDT = (parseFloat(usdtBalance?.free || '0') + parseFloat(usdtBalance?.locked || '0'))

    return {
      accountType: 'spot',
      totalAsset: totalUSDT.toFixed(2),
      availableBalance: usdtBalance?.free || '0',
      positionCount: 0,
      updateTime: spotAccount.value.updateTime
        ? new Date(spotAccount.value.updateTime).toLocaleString()
        : '-',
    }
  })

  /**
   * 期货账户概览
   */
  const futuresOverview = computed((): AccountOverview | null => {
    if (!futuresAccount.value) return null

    const positions = futuresAccount.value.positions || []
    const positionCount = positions.filter(p => parseFloat(p.positionAmt || '0') !== 0).length

    return {
      accountType: 'futures',
      totalAsset: futuresAccount.value.totalWalletBalance || '0',
      availableBalance: futuresAccount.value.availableBalance || futuresAccount.value.totalWalletBalance || '0',
      positionCount,
      updateTime: futuresAccount.value.updateTime
        ? new Date(futuresAccount.value.updateTime).toLocaleString()
        : '-',
    }
  })

  /**
   * 期货持仓列表
   *
   * 注意: /fapi/v3/account 返回的持仓数据是简化版本
   * 仅返回: symbol, positionSide, positionAmt, unrealizedProfit,
   *        isolatedMargin, notional, isolatedWallet, initialMargin, maintMargin, updateTime
   * 不返回: entryPrice, markPrice, liquidationPrice, leverage (这些需要 /fapi/v3/positionRisk)
   */
  const futuresPositions = computed((): PositionItem[] => {
    if (!futuresAccount.value?.positions) return []

    return futuresAccount.value.positions
      .filter(p => parseFloat(p.positionAmt || '0') !== 0)
      .map(p => ({
        symbol: p.symbol,
        // 持仓方向: BOTH(单向持仓), LONG(多头), SHORT(空头)
        side: (p.positionSide?.toLowerCase() || 'both') as 'long' | 'short' | 'both',
        // 持仓数量
        amount: p.positionAmt || '0',
        // 开仓价格 (V3 API 不返回，显示为 -)
        entryPrice: '-',
        // 标记价格 (V3 API 不返回，显示为 -)
        markPrice: '-',
        // 未实现盈亏
        unrealizedPnl: p.unrealizedProfit || '0',
        // 持仓保证金: 逐仓用 isolatedMargin，全仓用 initialMargin
        margin: p.isolatedMargin || p.initialMargin || '0',
        // 强平价格 (V3 API 不返回，显示为 -)
        liquidationPrice: '-',
        // 名义价值
        notional: p.notional || '0',
      }))
  })

  /**
   * 期货资产列表
   */
  const futuresAssets = computed(() => {
    if (!futuresAccount.value?.assets) return []
    return futuresAccount.value.assets
  })

  /**
   * 现货余额列表
   */
  const spotBalances = computed((): BalanceItem[] => {
    if (!spotAccount.value?.balances) return []

    return spotAccount.value.balances
      .map(b => {
        const free = parseFloat(b.free || '0')
        const locked = parseFloat(b.locked || '0')
        return {
          asset: b.asset,
          free: b.free || '0',
          locked: b.locked || '0',
          total: (free + locked).toString(),
        }
      })
      .filter(b => parseFloat(b.total) > 0)
      .sort((a, b) => parseFloat(b.total) - parseFloat(a.total))
  })

  // ==================== WebSocket 基础方法 ====================

  /**
   * 发送 WebSocket 消息并等待响应
   */
  function sendWSRequest<T>(message: Record<string, unknown>): Promise<T> {
    return new Promise((resolve, reject) => {
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket 未连接'))
        return
      }

      const requestId = message.requestId as string

      // 设置超时
      const timeoutId = window.setTimeout(() => {
        pendingRequests.delete(requestId)
        reject(new Error(`请求超时: ${requestId}`))
      }, REQUEST_TIMEOUT)

      // 存储回调
      pendingRequests.set(requestId, { resolve: resolve as (value: unknown) => void, reject, timeoutId })

      // 发送消息
      ws.value.send(JSON.stringify(message))
    })
  }

  /**
   * 构建基础请求消息
   * 使用 v2.0 协议: type 字段替代 action 字段
   */
  function buildRequestMessage(data: Record<string, unknown>): Record<string, unknown> {
    // 从 data.type 获取请求类型，映射到协议请求类型
    const dataType = data.type as string
    const typeMap: Record<string, string> = {
      'get_spot_account': 'GET_SPOT_ACCOUNT',
      'get_futures_account': 'GET_FUTURES_ACCOUNT',
    }
    return {
      protocolVersion: '2.0',
      type: typeMap[dataType] || dataType,
      requestId: generateRequestId('req_account'),
      timestamp: Date.now(),
      data,
    }
  }

  /**
   * 连接 WebSocket
   */
  function connectWebSocket() {
    // 如果已连接或正在连接，直接返回
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }
    if (wsConnecting.value) {
      return
    }

    wsConnecting.value = true

    try {
      ws.value = new WebSocket(`${WS_BASE_URL}/ws/market`)

      ws.value.onopen = () => {
        wsConnected.value = true
        wsConnecting.value = false
        console.debug('[AccountStore] WebSocket connected')
      }

      ws.value.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleWebSocketMessage(message)
        } catch (error) {
          console.warn('[AccountStore] Failed to parse WebSocket message:', error)
        }
      }

      ws.value.onerror = (error) => {
        console.warn('[AccountStore] WebSocket error:', error)
        wsConnecting.value = false
      }

      ws.value.onclose = () => {
        wsConnected.value = false
        wsConnecting.value = false
        console.debug('[AccountStore] WebSocket disconnected')
        // 自动重连（保存定时器引用以便清理）
        reconnectTimeoutId = window.setTimeout(() => {
          reconnectTimeoutId = null
          connectWebSocket()
        }, 3000)
      }
    } catch (error) {
      console.warn('[AccountStore] Failed to create WebSocket:', error)
      wsConnecting.value = false
    }
  }

  /**
   * 处理 WebSocket 消息
   * 使用 v2.0 协议: type 字段替代 action 字段
   */
  function handleWebSocketMessage(message: Record<string, unknown>) {
    const msgType = message.type as string
    const requestId = message.requestId as string

    // 处理 ack 确认响应
    if (msgType === 'ACK') {
      console.debug('[AccountStore] 收到 ACK 确认, requestId:', requestId)
      return
    }

    // 处理请求响应 - v2.0 使用具体数据类型
    if (msgType === 'ACCOUNT_DATA' || msgType === 'ERROR') {
      console.debug('[AccountStore] 收到响应, requestId:', requestId, 'type:', msgType, 'data:', JSON.stringify(message.data))
      const pending = pendingRequests.get(requestId)
      if (pending) {
        clearTimeout(pending.timeoutId)
        pendingRequests.delete(requestId)

        if (msgType === 'ACCOUNT_DATA') {
          pending.resolve(message.data)
        } else {
          const errorData = message.data as Record<string, unknown>
          const errorMsg = (errorData?.errorMessage || errorData?.message || 'Unknown error') as string
          pending.reject(errorMsg)
        }
      }
    }
  }

  // ==================== 账户 Actions ====================

  /**
   * 获取现货账户信息
   */
  async function fetchSpotAccount(): Promise<SpotAccountInfo | null> {
    // 确保 WebSocket 已连接
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connectWebSocket()
      // 等待连接建立（最多等待3秒）
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (ws.value?.readyState === WebSocket.OPEN) break
      }
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        spotError.value = 'WebSocket 连接失败'
        return null
      }
    }

    spotLoading.value = true
    spotError.value = null

    try {
      const message = buildRequestMessage({
        type: 'get_spot_account',
      })

      const response = await sendWSRequest<AccountResponse>(message)

      // 后端返回 content 字段为 JSON 对象
      const responseData = response as unknown as { content: SpotAccountInfo }
      spotAccount.value = responseData.content
      return spotAccount.value
    } catch (error) {
      spotError.value = error instanceof Error ? error.message : '获取现货账户信息失败'
      console.warn('fetchSpotAccount error:', error)
      return null
    } finally {
      spotLoading.value = false
    }
  }

  /**
   * 获取期货账户信息
   */
  async function fetchFuturesAccount(): Promise<FuturesAccountInfo | null> {
    // 确保 WebSocket 已连接
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connectWebSocket()
      // 等待连接建立（最多等待3秒）
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (ws.value?.readyState === WebSocket.OPEN) break
      }
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        futuresError.value = 'WebSocket 连接失败'
        return null
      }
    }

    futuresLoading.value = true
    futuresError.value = null

    try {
      const message = buildRequestMessage({
        type: 'get_futures_account',
      })

      const response = await sendWSRequest<AccountResponse>(message)

      // 后端返回 content 字段，前端转换为 account_info
      const responseData = response as unknown as { content: FuturesAccountInfo }
      futuresAccount.value = responseData.content
      return futuresAccount.value
    } catch (error) {
      futuresError.value = error instanceof Error ? error.message : '获取期货账户信息失败'
      console.warn('fetchFuturesAccount error:', error)
      return null
    } finally {
      futuresLoading.value = false
    }
  }

  /**
   * 刷新账户信息
   */
  async function refreshAccounts(): Promise<void> {
    await Promise.all([
      fetchSpotAccount(),
      fetchFuturesAccount(),
    ])
  }

  /**
   * 清除错误
   */
  function clearError() {
    spotError.value = null
    futuresError.value = null
  }

  /**
   * 断开 WebSocket
   */
  function disconnectWebSocket() {
    // 清除重连定时器
    if (reconnectTimeoutId !== null) {
      clearTimeout(reconnectTimeoutId)
      reconnectTimeoutId = null
    }

    // 清除所有待处理的请求
    for (const [_, pending] of pendingRequests) {
      clearTimeout(pending.timeoutId)
      pending.reject(new Error('WebSocket 连接关闭'))
    }
    pendingRequests.clear()

    if (ws.value) {
      ws.value.close()
      ws.value = null
      wsConnected.value = false
    }
  }

  // ==================== 初始化 ====================

  /**
   * 初始化 Store
   */
  function initialize() {
    console.debug('[AccountStore] 初始化 Store')
    connectWebSocket()
  }

  /**
   * 重置 Store
   */
  function reset() {
    // 清除重连定时器
    if (reconnectTimeoutId !== null) {
      clearTimeout(reconnectTimeoutId)
      reconnectTimeoutId = null
    }

    spotAccount.value = null
    spotLoading.value = false
    spotError.value = null
    futuresAccount.value = null
    futuresLoading.value = false
    futuresError.value = null
    disconnectWebSocket()
  }

  return {
    // ==================== 状态 ====================
    spotAccount,
    spotLoading,
    spotError,
    futuresAccount,
    futuresLoading,
    futuresError,
    wsConnected,

    // ==================== 计算属性 ====================
    spotOverview,
    futuresOverview,
    futuresPositions,
    futuresAssets,
    spotBalances,

    // ==================== Actions ====================
    fetchSpotAccount,
    fetchFuturesAccount,
    refreshAccounts,
    clearError,

    // ==================== WebSocket Actions ====================
    connectWebSocket,
    disconnectWebSocket,

    // ==================== 生命周期 ====================
    initialize,
    reset,
  }
})
