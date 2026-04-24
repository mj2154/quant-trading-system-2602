/**
 * 统一数据服务 - DataService 单例类
 *
 * 职责:
 * - 管理WebSocket连接
 * - 提供类型安全的GET请求方法
 * - 订阅管理（去重、状态维护）
 * - 自动重连
 *
 * 基于 types/api/ 目录下的类型定义
 */

import {
  PROTOCOL_VERSION,
  type WSMessage,
  type WSRequestMessage,
  type ClientRequestType,
  type GetKlinesResponse,
  type GetQuotesResponse,
  type AccountDataResponse,
  type SignalResponse,
  type StrategyMetadataListResponse,
  type StrategyMetadataResponse,
} from './types'
import type {
  GetKlinesParams,
  KlineBars,
  QuotesList,
  SpotAccountDetail,
  FuturesAccountDetail,
  SpotAccountData,
  FuturesAccountData,
  AlertConfig,
  AlertConfigListResponse,
  SignalRecord,
  OrderData,
  OrderListData,
  SubscriptionOptions,
  SubscriptionInfo,
  SubscriptionCallback,
  KlineBar,
  QuotesValue,
  AccountUpdate,
} from '../../types/api'

/**
 * 图表配置数据类型
 */
export interface DatafeedConfiguration {
  supports_search: boolean
  supports_group_request: boolean
  supported_resolutions: string[]
  intraday_multipliers: string[]
  symbols_types: Array<{ name: string; value: string }>
}

/**
 * 待处理的请求
 */
interface PendingRequest<T = unknown> {
  resolve: (value: T) => void
  reject: (error: Error) => void
  timeoutId: number
}

/**
 * 获取WebSocket URL
 */
function getWSUrl(): string {
  const wsHost = import.meta.env?.VITE_WS_HOST || 'localhost:8000'
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${wsHost}/ws`
}

/**
 * 生成UUID v4 hex格式的requestId
 */
export function generateRequestId(): string {
  return crypto.randomUUID().replace(/-/g, '')
}

/**
 * 统一数据服务类 - 单例模式
 *
 * 使用方式:
 * ```typescript
 * const dataService = DataService.getInstance()
 * await dataService.connect()
 *
 * // 获取K线数据
 * const klines = await dataService.getKlines({ symbol: 'BINANCE:BTCUSDT', interval: '60' })
 *
 * // 获取报价
 * const quotes = await dataService.getQuotes(['BINANCE:BTCUSDT'])
 * ```
 */
export class DataService {
  private static instance: DataService
  private ws: WebSocket | null = null

  // 连接状态
  private connected = false
  private connecting = false

  // 待处理的请求 (requestId -> pending request)
  private pendingRequests = new Map<string, PendingRequest>()

  // 消息处理器 (subscriptionKey -> handler)
  private messageHandlers = new Map<string, Set<(data: unknown, subscriptionKey: string) => void>>()

  // 订阅信息存储 (subscriptionKey -> SubscriptionInfo)
  private subscriptionInfos = new Map<string, SubscriptionInfo>()

  // 重连定时器
  private reconnectTimeoutId: number | null = null

  // 连接回调
  private onConnectCallback: (() => void) | null = null
  private onDisconnectCallback: (() => void) | null = null

  // 私有构造函数确保单例
  private constructor() {}

  // ==================== 单例管理 ====================

  /**
   * 获取单例实例
   */
  static getInstance(): DataService {
    if (!DataService.instance) {
      DataService.instance = new DataService()
    }
    return DataService.instance
  }

  // ==================== 连接管理 ====================

  /**
   * 设置连接回调
   */
  onConnect(callback: () => void): void {
    this.onConnectCallback = callback
  }

  /**
   * 设置断开连接回调
   */
  onDisconnect(callback: () => void): void {
    this.onDisconnectCallback = callback
  }

  /**
   * 初始化并连接到WebSocket服务器
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      // 如果已连接，直接resolve
      if (this.connected) {
        resolve()
        return
      }

      // 如果正在连接，等待连接完成
      if (this.connecting) {
        const checkConnection = () => {
          if (this.connected) {
            resolve()
          } else if (!this.connecting) {
            reject(new Error('Connection failed'))
          } else {
            setTimeout(checkConnection, 50)
          }
        }
        checkConnection()
        return
      }

      this.connecting = true

      try {
        this.ws = new WebSocket(getWSUrl())

        this.ws.onopen = () => {
          this.connected = true
          this.connecting = false
          this.onConnectCallback?.()
          this.restoreSubscriptions()
          resolve()
        }

        this.ws.onclose = () => {
          this.handleDisconnect()
        }

        this.ws.onerror = () => {
          if (!this.connected) {
            this.connecting = false
            reject(new Error('WebSocket connection failed'))
          }
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data)
        }
      } catch (error) {
        this.connecting = false
        reject(error)
      }
    })
  }

  /**
   * 处理连接断开
   */
  private handleDisconnect(): void {
    const wasConnected = this.connected

    this.connected = false
    this.ws = null

    // 清除所有待处理的请求
    for (const [, pending] of this.pendingRequests) {
      clearTimeout(pending.timeoutId)
      pending.reject(new Error('Connection closed'))
    }
    this.pendingRequests.clear()

    if (wasConnected) {
      this.onDisconnectCallback?.()
    }

    // 自动重连
    this.scheduleReconnect()
  }

  /**
   * 调度重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimeoutId !== null) {
      return
    }

    this.reconnectTimeoutId = window.setTimeout(() => {
      this.reconnectTimeoutId = null

      if (!this.connected) {
        this.connect().catch(() => {
          // 连接失败时会自动调度重连
        })
      }
    }, 3000)
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    if (this.reconnectTimeoutId !== null) {
      clearTimeout(this.reconnectTimeoutId)
      this.reconnectTimeoutId = null
    }

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    // 清除所有待处理的请求
    for (const [, pending] of this.pendingRequests) {
      clearTimeout(pending.timeoutId)
      pending.reject(new Error('Connection closed'))
    }
    this.pendingRequests.clear()

    this.connected = false
    this.connecting = false

    this.onDisconnectCallback?.()
  }

  /**
   * 获取连接状态
   */
  get isConnected(): boolean {
    return this.connected
  }

  /**
   * 确保已连接
   */
  private async ensureConnected(): Promise<WebSocket> {
    if (!this.connected || !this.ws) {
      await this.connect()
    }
    return this.ws!
  }

  // ==================== 消息处理 ====================

  /**
   * 处理接收到的消息
   */
  private handleMessage(data: string): void {
    try {
      const message: WSMessage = JSON.parse(data)

      // 根据消息类型分发处理
      const messageType = message.type

      // 1. 处理ACK确认
      if (messageType === 'ACK') {
        return
      }

      // 2. 处理错误响应
      if (messageType === 'ERROR') {
        const requestId = message.requestId
        if (!requestId) return
        const pending = this.pendingRequests.get(requestId)

        if (pending) {
          clearTimeout(pending.timeoutId)
          this.pendingRequests.delete(requestId)

          const errorData = message.data as { errorCode?: string; errorMessage?: string } | undefined
          const error = new Error(
            `${errorData?.errorCode || 'ERROR'}: ${errorData?.errorMessage || 'Unknown error'}`
          )
          pending.reject(error)
        }
        return
      }

      // 3. 处理推送消息 (UPDATE)
      if (messageType === 'UPDATE') {
        this.handlePushMessage(message)
        return
      }

      // 4. 处理订单更新推送
      if (messageType === 'ORDER_UPDATE') {
        this.handlePushMessage(message)
        return
      }

      // 5. 处理成功响应 (带requestId)
      const requestId = message.requestId
      if (requestId) {
        const pending = this.pendingRequests.get(requestId)

        if (pending) {
          clearTimeout(pending.timeoutId)
          this.pendingRequests.delete(requestId)
          pending.resolve(message.data as never)
        }
      }
    } catch (error) {
      console.error('[DataService] Failed to parse message:', error)
    }
  }

  /**
   * 处理推送消息
   */
  private handlePushMessage(message: WSMessage): void {
    // 从消息顶层获取 subscriptionKey
    const subscriptionKey = (message as unknown as { subscriptionKey?: string }).subscriptionKey

    if (!subscriptionKey) {
      console.warn('[DataService] UPDATE message missing subscriptionKey')
      return
    }

    // 从消息获取 data（直接载荷，无 content 包装）
    const content = message.data

    const handlers = this.messageHandlers.get(subscriptionKey)

    if (handlers && handlers.size > 0) {
      console.debug('[DataService] 收到推送消息, subscriptionKey:', subscriptionKey, 'handlers数量:', handlers.size)
      handlers.forEach((handler) => {
        handler(content, subscriptionKey)
      })
    } else {
      // 无 handler 静默忽略
      console.debug('[DataService] subscriptionKey 没有 handler:', subscriptionKey)
      console.debug('[DataService] 当前所有 subscriptionKeys:', Array.from(this.messageHandlers.keys()))
    }
  }

  // ==================== 发送消息 ====================

  /**
   * 发送WebSocket消息
   */
  private sendMessage(message: WSRequestMessage): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[DataService] Cannot send message: WebSocket not connected')
      return
    }
    this.ws.send(JSON.stringify(message))
  }

  /**
   * 发送请求并等待响应
   */
  async request<T = unknown>(
    requestType: ClientRequestType,
    data?: Record<string, unknown>
  ): Promise<T> {
    // 确保已连接
    await this.ensureConnected()

    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'))
        return
      }

      const requestId = generateRequestId()

      // 设置超时 (30秒)
      const timeoutId = window.setTimeout(() => {
        this.pendingRequests.delete(requestId)
        reject(new Error(`Request ${requestType} timed out`))
      }, 30000)

      // 存储pending request
      this.pendingRequests.set(requestId, {
        resolve: resolve as (value: unknown) => void,
        reject,
        timeoutId,
      })

      // 构建请求消息
      const request: WSRequestMessage = {
        protocolVersion: PROTOCOL_VERSION,
        type: requestType,
        requestId,
        timestamp: Date.now(),
        data,
      }

      // 发送消息
      this.sendMessage(request)
    })
  }

  /**
   * 发送订阅/取消订阅命令
   */
  private sendSubscription(type: 'SUBSCRIBE' | 'UNSUBSCRIBE', subscriptionKeys: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[DataService] Cannot send subscription: WebSocket not connected')
      return
    }

    if (subscriptionKeys.length === 0) {
      return
    }

    const requestId = generateRequestId()

    const message: WSRequestMessage = {
      protocolVersion: PROTOCOL_VERSION,
      type,
      requestId,
      timestamp: Date.now(),
      data: {
        subscriptions: subscriptionKeys,
      },
    }

    this.sendMessage(message)
    // 静默发送
  }

  // ==================== 恢复订阅 ====================

  /**
   * 恢复之前的订阅
   */
  private restoreSubscriptions(): void {
    for (const [key, info] of this.subscriptionInfos) {
      if (info.options.reconnect !== false && info.status === 'active') {
        // 只重发订阅命令，handlers 由业务层在 onConnect 回调中显式订阅
        this.sendSubscription('SUBSCRIBE', [key])
      }
    }
  }

  // ==================== 市场数据 ====================

  /**
   * 获取K线数据
   */
  async getKlines(params: GetKlinesParams): Promise<KlineBars> {
    const ws = await this.ensureConnected()

    const requestParams: Record<string, unknown> = {
      symbol: params.symbol,
      interval: params.interval,
    }

    if (params.fromTime !== undefined) {
      requestParams.fromTime = params.fromTime
    }
    if (params.toTime !== undefined) {
      requestParams.toTime = params.toTime
    }
    if (params.limit !== undefined) {
      requestParams.limit = params.limit
    }

    const response = await this.request<GetKlinesResponse>('GET_KLINES', requestParams)

    return {
      symbol: response.symbol,
      interval: response.interval,
      bars: response.bars || [],
      count: response.count || 0,
      noData: response.noData ?? true,
      nextTime: response.nextTime,
    }
  }

  /**
   * 获取报价数据
   */
  async getQuotes(symbols: string[]): Promise<QuotesList> {
    await this.ensureConnected()

    const response = await this.request<GetQuotesResponse>('GET_QUOTES', { symbols })

    return {
      quotes: (response.quotes || []) as QuotesList['quotes'],
    }
  }

  /**
   * 获取图表数据源配置
   */
  async getConfig(): Promise<DatafeedConfiguration> {
    await this.ensureConnected()

    const response = await this.request<{ config: DatafeedConfiguration }>('GET_CONFIG')

    return {
      ...response.config,
      supports_group_request: true,
    }
  }

  // ==================== 账户数据 ====================

  /**
   * 获取现货账户信息
   */
  async getSpotAccount(): Promise<SpotAccountDetail> {
    await this.ensureConnected()

    const response = await this.request<AccountDataResponse>('GET_SPOT_ACCOUNT')

    // response.account 是 SpotAccountData，需取其内部的 account 字段
    return (response.account as SpotAccountData).account as SpotAccountDetail
  }

  /**
   * 获取期货账户信息
   */
  async getFuturesAccount(): Promise<FuturesAccountDetail> {
    await this.ensureConnected()

    const response = await this.request<AccountDataResponse>('GET_FUTURES_ACCOUNT')

    // response.account 是 FuturesAccountData，需取其内部的 account 字段
    return (response.account as FuturesAccountData).account as FuturesAccountDetail
  }

  // ==================== 告警管理 ====================

  /**
   * 获取告警配置列表
   */
  async listAlertConfigs(page = 1, pageSize = 20): Promise<AlertConfig[]> {
    await this.ensureConnected()

    const response = await this.request<AlertConfigListResponse>('LIST_ALERT_CONFIGS', {
      page,
      pageSize,
    })

    return (response.items || []).map((item) => {
      const rawItem = item as unknown as Record<string, unknown>
      return {
        ...item,
        strategyType: (rawItem.strategyType as string) || (rawItem.strategy_type as string) || '',
        symbol: (rawItem.symbol as string) || '',
        interval: (rawItem.interval as string) || '60',
        triggerType: (rawItem.triggerType as string) || (rawItem.trigger_type as string) || 'each_kline_close',
        params: this.convertParamsFromBackend(item.params) || {
          macd1_fastperiod: 12,
          macd1_slowperiod: 26,
          macd1_signalperiod: 9,
          macd2_fastperiod: 5,
          macd2_slowperiod: 10,
          macd2_signalperiod: 4,
        },
        isEnabled: (rawItem.isEnabled as boolean) ?? (rawItem.is_enabled as boolean) ?? true,
        createdAt: (rawItem.createdAt as string) || (rawItem.created_at as string) || '',
        updatedAt: (rawItem.updatedAt as string) || (rawItem.updated_at as string) || '',
        createdBy: (rawItem.createdBy as string) || (rawItem.created_by as string) || undefined,
      }
    })
  }

  /**
   * 获取单个告警配置
   */
  async getAlert(id: string): Promise<AlertConfig | null> {
    await this.ensureConnected()

    const response = await this.request<AlertConfigListResponse>('LIST_ALERT_CONFIGS', {
      limit: 1,
      offset: 0,
    })

    if (!response.items || response.items.length === 0) {
      return null
    }

    const alert = response.items[0]
    const rawItem = alert as unknown as Record<string, unknown>
    return {
      ...alert,
      strategyType: (rawItem.strategyType as string) || (rawItem.strategy_type as string) || '',
      symbol: (rawItem.symbol as string) || '',
      interval: (rawItem.interval as string) || '60',
      triggerType: (rawItem.triggerType as string) || (rawItem.trigger_type as string) || 'each_kline_close',
      params: this.convertParamsFromBackend(alert.params) || {
        macd1_fastperiod: 12,
        macd1_slowperiod: 26,
        macd1_signalperiod: 9,
        macd2_fastperiod: 5,
        macd2_slowperiod: 10,
        macd2_signalperiod: 4,
      },
      isEnabled: (rawItem.isEnabled as boolean) ?? (rawItem.is_enabled as boolean) ?? true,
      createdAt: (rawItem.createdAt as string) || (rawItem.created_at as string) || '',
      updatedAt: (rawItem.updatedAt as string) || (rawItem.updated_at as string) || '',
      createdBy: (rawItem.createdBy as string) || (rawItem.created_by as string) || undefined,
    }
  }

  /**
   * 创建告警配置
   */
  async createAlert(config: {
    name: string
    description?: string
    strategyType: string
    symbol: string
    interval: string
    triggerType?: string
    params?: Record<string, number | boolean>
    isEnabled?: boolean
  }): Promise<AlertConfig> {
    await this.ensureConnected()

    const params = this.convertParamsToBackend(config.params)

    const response = await this.request<AlertConfig>('CREATE_ALERT_CONFIG', {
      id: crypto.randomUUID().replace(/-/g, ''),
      name: config.name,
      description: config.description || '',
      strategyType: config.strategyType,
      symbol: config.symbol,
      interval: config.interval,
      triggerType: config.triggerType || 'each_kline_close',
      params,
      isEnabled: config.isEnabled ?? true,
      createdBy: 'local_user',
    })

    return {
      ...response,
      params: this.convertParamsFromBackend(response.params),
    }
  }

  /**
   * 更新告警配置
   */
  async updateAlert(
    id: string,
    updates: {
      name?: string
      description?: string
      strategyType?: string
      symbol?: string
      interval?: string
      triggerType?: string
      params?: Record<string, number | boolean>
      isEnabled?: boolean
    }
  ): Promise<AlertConfig> {
    await this.ensureConnected()

    const params = updates.params ? this.convertParamsToBackend(updates.params) : undefined

    const requestData: Record<string, unknown> = { id }
    if (updates.name !== undefined) requestData.name = updates.name
    if (updates.description !== undefined) requestData.description = updates.description
    if (updates.strategyType !== undefined) requestData.strategyType = updates.strategyType
    if (updates.symbol !== undefined) requestData.symbol = updates.symbol
    if (updates.interval !== undefined) requestData.interval = updates.interval
    if (updates.triggerType !== undefined) requestData.triggerType = updates.triggerType
    if (params !== undefined) requestData.params = params
    if (updates.isEnabled !== undefined) requestData.isEnabled = updates.isEnabled

    const response = await this.request<AlertConfig>('UPDATE_ALERT_CONFIG', requestData)

    return {
      ...response,
      params: this.convertParamsFromBackend(response.params),
    }
  }

  /**
   * 删除告警配置
   */
  async deleteAlert(id: string): Promise<boolean> {
    await this.ensureConnected()

    await this.request<{ success: boolean }>('DELETE_ALERT_CONFIG', { id })
    return true
  }

  /**
   * 启用告警
   */
  async enableAlert(id: string): Promise<{ id: string; isEnabled: boolean }> {
    await this.ensureConnected()

    const response = await this.request<{ id: string; isEnabled: boolean }>('UPDATE_ALERT_CONFIG', {
      id,
      isEnabled: true,
    })

    return response
  }

  /**
   * 禁用告警
   */
  async disableAlert(id: string): Promise<{ id: string; isEnabled: boolean }> {
    await this.ensureConnected()

    const response = await this.request<{ id: string; isEnabled: boolean }>('UPDATE_ALERT_CONFIG', {
      id,
      isEnabled: false,
    })

    return response
  }

  // ==================== 参数转换 ====================

  /**
   * 将前端参数转换为后端API格式
   */
  private convertParamsToBackend(params?: Record<string, number | boolean>): Record<string, number | boolean> {
    const defaultParams: Record<string, number> = {
      macd1_fastperiod: 12,
      macd1_slowperiod: 26,
      macd1_signalperiod: 9,
      macd2_fastperiod: 5,
      macd2_slowperiod: 10,
      macd2_signalperiod: 4,
    }

    if (!params || Object.keys(params).length === 0) {
      return { ...defaultParams }
    }

    return { ...params }
  }

  /**
   * 将后端返回的参数转换为前端格式
   */
  private convertParamsFromBackend(params?: Record<string, unknown> | null): Record<string, number | boolean> {
    if (!params || Object.keys(params).length === 0) {
      return {}
    }

    const converted: Record<string, number | boolean> = {}
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === 'number' || typeof value === 'boolean') {
        converted[key] = value
      }
    }
    return converted
  }

  // ==================== 信号管理 ====================

  /**
   * 获取信号列表
   */
  async listSignals(params?: {
    page?: number
    pageSize?: number
    symbol?: string
    strategyType?: string
    interval?: string
    signalValue?: boolean
    fromTime?: number
    toTime?: number
  }): Promise<SignalRecord[]> {
    await this.ensureConnected()

    const response = await this.request<SignalResponse>('LIST_SIGNALS', params || {})

    return response.items || []
  }

  // ==================== 订单管理 ====================

  /**
   * 获取订单列表
   */
  async listOrders(params?: {
    symbol?: string
    status?: string
    startTime?: number
    endTime?: number
    limit?: number
  }): Promise<OrderListData> {
    await this.ensureConnected()

    const response = await this.request<OrderListData>('LIST_ORDERS', params || {})

    return response
  }

  /**
   * 获取当前挂单
   */
  async getOpenOrders(symbol?: string): Promise<OrderListData> {
    await this.ensureConnected()

    const params = symbol ? { symbol } : {}
    const response = await this.request<OrderListData>('GET_OPEN_ORDERS', params)

    return response
  }

  // ==================== 策略元数据 ====================

  /**
   * 获取所有策略元数据列表
   */
  async getStrategyMetadata(): Promise<StrategyMetadataResponse[]> {
    await this.ensureConnected()

    const response = await this.request<StrategyMetadataListResponse>('GET_STRATEGY_METADATA')

    return response.strategies || []
  }

  /**
   * 获取指定策略的元数据
   */
  async getStrategyMetadataByType(strategyType: string): Promise<StrategyMetadataResponse | null> {
    await this.ensureConnected()

    const response = await this.request<{ strategy: StrategyMetadataResponse }>('GET_STRATEGY_METADATA_BY_TYPE', {
      strategyType,
    })

    return response.strategy || null
  }

  /**
   * 获取订单详情
   */
  async getOrder(params: { symbol: string; orderId?: number; origClientOrderId?: string }): Promise<OrderData> {
    await this.ensureConnected()

    const response = await this.request<{ order: OrderData }>('GET_ORDER', params)

    return response.order
  }

  /**
   * 创建订单
   */
  async createOrder(params: {
    symbol: string
    side: string
    type: string
    quantity?: number | string
    quoteOrderQty?: number | string
    price?: number | string
    timeInForce?: string
    stopPrice?: number | string
    reduceOnly?: boolean
    positionSide?: string
    newClientOrderId?: string
    icebergQty?: number | string
    trailingDelta?: number
    strategyId?: number
    strategyType?: number
    selfTradePreventionMode?: string
  }): Promise<OrderData> {
    await this.ensureConnected()

    const clientOrderId = params.newClientOrderId || crypto.randomUUID().replace(/-/g, '')

    const response = await this.request<{ order: OrderData }>('CREATE_ORDER', {
      symbol: params.symbol,
      side: params.side,
      type: params.type,
      quantity: params.quantity?.toString(),
      quoteOrderQty: params.quoteOrderQty?.toString(),
      price: params.price?.toString(),
      timeInForce: params.timeInForce,
      stopPrice: params.stopPrice?.toString(),
      reduceOnly: params.reduceOnly,
      positionSide: params.positionSide,
      newClientOrderId: clientOrderId,
      icebergQty: params.icebergQty?.toString(),
      trailingDelta: params.trailingDelta,
      strategyId: params.strategyId,
      strategyType: params.strategyType,
      selfTradePreventionMode: params.selfTradePreventionMode,
    })

    return response.order
  }

  /**
   * 取消订单
   */
  async cancelOrder(params: { symbol: string; orderId?: number; origClientOrderId?: string }): Promise<OrderData> {
    await this.ensureConnected()

    const response = await this.request<{ order: OrderData }>('CANCEL_ORDER', params)

    return response.order
  }

  // ==================== 订阅管理 ====================

  /**
   * 注册消息处理器
   */
  private addHandler(subscriptionKey: string, handler: (data: unknown, subscriptionKey: string) => void): void {
    let handlers = this.messageHandlers.get(subscriptionKey)
    if (!handlers) {
      handlers = new Set()
      this.messageHandlers.set(subscriptionKey, handlers)
    }
    handlers.add(handler)
  }

  /**
   * 移除消息处理器
   */
  private removeHandler(subscriptionKey: string, handler?: (data: unknown, subscriptionKey: string) => void): void {
    const handlers = this.messageHandlers.get(subscriptionKey)
    if (!handlers) return

    if (handler) {
      handlers.delete(handler)
      if (handlers.size === 0) {
        this.messageHandlers.delete(subscriptionKey)
      }
    } else {
      this.messageHandlers.delete(subscriptionKey)
    }
  }

  /**
   * 检查是否存在处理器
   */
  private hasHandler(subscriptionKey: string): boolean {
    const handlers = this.messageHandlers.get(subscriptionKey)
    return handlers !== undefined && handlers.size > 0
  }

  /**
   * 订阅实时数据
   */
  subscribe(subscriptionKey: string, handler: (data: unknown, subscriptionKey?: string) => void): () => void {
    // 检查是否已有 handler
    if (!this.hasHandler(subscriptionKey)) {
      // 首次订阅：发送订阅命令
      this.sendSubscription('SUBSCRIBE', [subscriptionKey])
    }

    // 注册 handler
    this.addHandler(subscriptionKey, (data, sk) => {
      handler(data, sk)
    })

    // 记录订阅信息
    this.subscriptionInfos.set(subscriptionKey, {
      key: subscriptionKey,
      callback: handler as SubscriptionCallback<unknown>,
      options: { reconnect: true },
      subscribedAt: Date.now(),
      status: 'active',
    })

    // 返回取消订阅函数
    return () => {
      this.unsubscribe(subscriptionKey)
    }
  }

  /**
   * 取消订阅
   */
  unsubscribe(subscriptionKey: string): void {
    // 发送取消订阅命令
    this.sendSubscription('UNSUBSCRIBE', [subscriptionKey])

    // 移除 handler
    this.removeHandler(subscriptionKey)

    // 删除订阅信息
    this.subscriptionInfos.delete(subscriptionKey)
  }

  /**
   * 获取当前所有订阅
   */
  getSubscriptions(): string[] {
    return Array.from(this.messageHandlers.keys())
  }

  // ==================== 类型安全订阅方法 ====================

  /**
   * 订阅K线实时数据
   */
  subscribeKline(
    symbol: string,
    interval: string,
    callback: (bar: KlineBar, subscriptionKey: string) => void,
    options?: SubscriptionOptions
  ): () => void {
    const subscriptionKey = `${symbol}@KLINE_${interval}`
    const finalOptions: SubscriptionOptions = { reconnect: true, ...options }

    // 存储订阅信息
    this.subscriptionInfos.set(subscriptionKey, {
      key: subscriptionKey,
      callback: callback as SubscriptionCallback<unknown>,
      options: finalOptions,
      subscribedAt: Date.now(),
      status: 'active',
    })

    // 实际订阅
    const unsubscribe = this.subscribe(subscriptionKey, (data, sk) => {
      callback(data as KlineBar, sk || subscriptionKey)
    })

    // 返回包装的取消订阅函数
    return () => {
      unsubscribe()
      this.subscriptionInfos.delete(subscriptionKey)
    }
  }

  /**
   * 订阅报价实时数据
   */
  subscribeQuotes(
    symbols: string[],
    callback: (quotes: Map<string, QuotesValue>) => void,
    options?: SubscriptionOptions
  ): () => void {
    const finalOptions: SubscriptionOptions = { reconnect: true, ...options }
    const quotesMap = new Map<string, QuotesValue>()

    // 收集所有 subscriptionKeys
    const subscriptionKeys: string[] = []
    const keysToSubscribe: string[] = []

    for (const symbol of symbols) {
      const subscriptionKey = `${symbol}@QUOTES`
      subscriptionKeys.push(subscriptionKey)

      // 构建 handler
      const handler = (data: unknown) => {
        const quoteData = data as QuotesValue
        quotesMap.set(symbol, quoteData)
        callback(new Map(quotesMap))
      }

      // 只对未订阅的 key 发送订阅命令
      if (!this.hasHandler(subscriptionKey)) {
        keysToSubscribe.push(subscriptionKey)
      }

      // 注册 handler
      this.addHandler(subscriptionKey, handler)

      // 存储订阅信息
      this.subscriptionInfos.set(subscriptionKey, {
        key: subscriptionKey,
        callback: handler as SubscriptionCallback<unknown>,
        options: finalOptions,
        subscribedAt: Date.now(),
        status: 'active',
      })
    }

    // 批量发送订阅命令
    if (keysToSubscribe.length > 0) {
      this.sendSubscription('SUBSCRIBE', keysToSubscribe)
    }

    // 返回批量取消订阅函数
    return () => {
      for (const key of subscriptionKeys) {
        this.unsubscribe(key)
      }
    }
  }

  /**
   * 订阅账户增量更新
   */
  subscribeAccount(
    accountType: 'SPOT' | 'FUTURES',
    callback: (update: AccountUpdate) => void,
    options?: SubscriptionOptions
  ): () => void {
    // 订阅键格式: BINANCE:SPOT@USERDATA 或 BINANCE:FUTURES@USERDATA (遵循WS协议文档)
    const subscriptionKey = `BINANCE:${accountType}@USERDATA`
    const finalOptions: SubscriptionOptions = { reconnect: true, ...options }

    this.subscriptionInfos.set(subscriptionKey, {
      key: subscriptionKey,
      callback: callback as SubscriptionCallback<unknown>,
      options: finalOptions,
      subscribedAt: Date.now(),
      status: 'active',
    })

    const unsubscribe = this.subscribe(subscriptionKey, (data, sk) => {
      callback(data as AccountUpdate)
    })

    return () => {
      unsubscribe()
      this.subscriptionInfos.delete(subscriptionKey)
    }
  }

  /**
   * 订阅信号实时推送
   */
  subscribeSignal(
    alertId: string,
    callback: (signal: SignalRecord) => void,
    options?: SubscriptionOptions
  ): () => void {
    const subscriptionKey = `SIGNAL:${alertId}`
    const finalOptions: SubscriptionOptions = { reconnect: true, ...options }

    this.subscriptionInfos.set(subscriptionKey, {
      key: subscriptionKey,
      callback: callback as SubscriptionCallback<unknown>,
      options: finalOptions,
      subscribedAt: Date.now(),
      status: 'active',
    })

    const unsubscribe = this.subscribe(subscriptionKey, (data, sk) => {
      callback(data as SignalRecord)
    })

    return () => {
      unsubscribe()
      this.subscriptionInfos.delete(subscriptionKey)
    }
  }

  /**
   * 批量订阅信号
   */
  subscribeAllSignals(
    alertIds: string[],
    callback: (signal: SignalRecord) => void
  ): () => void {
    if (alertIds.length === 0) {
      return () => {}
    }

    const unsubscribers: Array<() => void> = []

    for (const alertId of alertIds) {
      const subscriptionKey = `SIGNAL:${alertId}`

      // 存储订阅信息
      this.subscriptionInfos.set(subscriptionKey, {
        key: subscriptionKey,
        callback: callback as SubscriptionCallback<unknown>,
        options: { reconnect: true },
        subscribedAt: Date.now(),
        status: 'active',
      })

      const unsub = this.subscribe(subscriptionKey, (data) => {
        callback(data as SignalRecord)
      })
      unsubscribers.push(unsub)
    }

    return () => {
      for (const unsub of unsubscribers) {
        unsub()
      }
      for (const alertId of alertIds) {
        this.subscriptionInfos.delete(`SIGNAL:${alertId}`)
      }
    }
  }

  // ==================== 订阅信息管理 ====================

  /**
   * 获取订阅信息
   */
  getSubscriptionInfo(subscriptionKey: string): SubscriptionInfo | undefined {
    return this.subscriptionInfos.get(subscriptionKey)
  }

  /**
   * 获取所有订阅信息
   */
  getAllSubscriptionInfos(): SubscriptionInfo[] {
    return Array.from(this.subscriptionInfos.values())
  }

  /**
   * 清空所有订阅信息
   */
  clearSubscriptions(): void {
    // 取消所有WS订阅
    const keys = Array.from(this.messageHandlers.keys())
    if (keys.length > 0) {
      this.sendSubscription('UNSUBSCRIBE', keys)
    }
    this.messageHandlers.clear()
    this.subscriptionInfos.clear()
  }

  // ==================== 批量订阅 ====================

  /**
   * 批量订阅 (遵循协议: 50个/包, 250ms间隔)
   */
  subscribeBatch(
    subscriptions: Array<{
      key: string
      callback: (data: unknown, subscriptionKey?: string) => void
      options?: SubscriptionOptions
    }>
  ): () => void {
    const unsubscribers: Array<() => void> = []
    const BATCH_SIZE = 50
    const BATCH_DELAY = 250

    const processBatch = async (keys: string[]) => {
      for (const sub of subscriptions.filter((s) => keys.includes(s.key))) {
        const finalOptions: SubscriptionOptions = { reconnect: true, ...sub.options }

        this.subscriptionInfos.set(sub.key, {
          key: sub.key,
          callback: sub.callback as SubscriptionCallback<unknown>,
          options: finalOptions,
          subscribedAt: Date.now(),
          status: 'active',
        })

        const unsub = this.subscribe(sub.key, sub.callback)
        unsubscribers.push(unsub)

        // 批量发送时添加延迟
        if (keys.indexOf(sub.key) > 0 && keys.indexOf(sub.key) % BATCH_SIZE === 0) {
          await new Promise((resolve) => setTimeout(resolve, BATCH_DELAY))
        }
      }
    }

    // 将订阅分批处理
    const keys = subscriptions.map((s) => s.key)
    const batches: string[][] = []
    for (let i = 0; i < keys.length; i += BATCH_SIZE) {
      batches.push(keys.slice(i, i + BATCH_SIZE))
    }

    // 依次处理每批
    for (const batch of batches) {
      processBatch(batch)
    }

    // 返回批量取消订阅函数
    return () => {
      for (const unsub of unsubscribers) {
        unsub()
      }
      for (const sub of subscriptions) {
        this.subscriptionInfos.delete(sub.key)
      }
    }
  }
}

// 导出默认实例
export const dataService = DataService.getInstance()
