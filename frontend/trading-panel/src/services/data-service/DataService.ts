/**
 * 统一数据服务 - DataService 单例类
 *
 * 职责:
 * - 管理单一WebSocket连接
 * - 提供类型安全的GET请求方法
 * - 自动重连
 *
 * 基于 types/api/ 目录下的类型定义
 */

import { WSClient } from '../../libs/ws-client/WSClient'
import {
  type WSClientOptions,
  DEFAULT_WS_CLIENT_OPTIONS,
  type GetKlinesResponse,
  type GetQuotesResponse,
  type AccountDataResponse,
  type OrderResponse,
  type OrderListResponseData,
  type AlertConfigResponse,
  type AlertConfigOperationResponse,
  type SignalResponse,
  type StrategyMetadataListResponse,
  type StrategyMetadataResponse,
} from '../../libs/ws-client/types'
import type {
  GetKlinesParams,
  KlineBars,
  QuotesList,
  SpotAccountInfo,
  FuturesAccountInfo,
  AlertConfig,
  SignalRecord,
  Order,
  OrderListData,
  SubscriptionOptions,
  SubscriptionInfo,
  SubscriptionCallback,
  KlineBar,
  QuotesValue,
  TradeData,
  AccountUpdate,
  KlineSubscriptionOptions,
  QuotesSubscriptionOptions,
  AccountSubscriptionOptions,
  SignalSubscriptionOptions,
} from '../../types/api'

/**
 * 获取WebSocket URL
 */
function getWSUrl(): string {
  const wsHost = import.meta.env?.VITE_WS_HOST || 'localhost:8000'
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${wsHost}/ws`
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
  private wsClient: WSClient | null = null

  // 订阅信息存储 (subscriptionKey -> SubscriptionInfo)
  private subscriptionInfos = new Map<string, SubscriptionInfo>()

  // 待恢复的订阅 (用于重连后自动恢复)
  private pendingSubscriptions: Array<{ key: string; options: SubscriptionOptions }> = []

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
   * 初始化并连接到WebSocket服务器
   */
  async connect(): Promise<void> {
    if (!this.wsClient) {
      const options: WSClientOptions = {
        ...DEFAULT_WS_CLIENT_OPTIONS,
        url: getWSUrl(),
        autoReconnect: true,
        reconnectInterval: 3000,
        requestTimeout: 30000,
      }
      this.wsClient = new WSClient(options)
    }
    await this.wsClient.connect()

    // 连接成功后恢复之前的订阅
    this.restoreSubscriptions()
  }

  /**
   * 恢复之前的订阅
   */
  private restoreSubscriptions(): void {
    for (const [key, info] of this.subscriptionInfos) {
      if (info.options.reconnect !== false && info.status === 'active') {
        // 重新发送订阅消息
        this.wsClient?.subscribe(key, (data, sk) => {
          info.callback(data as never, sk)
        })
      }
    }
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.wsClient?.disconnect()
    this.wsClient = null
  }

  /**
   * 获取连接状态
   */
  get isConnected(): boolean {
    return this.wsClient?.isConnected ?? false
  }

  /**
   * 确保已连接
   */
  private async ensureConnected(): Promise<WSClient> {
    if (!this.wsClient || !this.wsClient.isConnected) {
      await this.connect()
    }
    return this.wsClient!
  }

  // ==================== 市场数据 ====================

  /**
   * 获取K线数据
   *
   * @param params - 获取K线请求参数
   * @returns K线数据
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

    const response = await ws.request<GetKlinesResponse>('GET_KLINES', requestParams)

    // 转换响应格式为 KlineBars
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
   *
   * @param symbols - 交易对列表
   * @returns 报价数据列表
   */
  async getQuotes(symbols: string[]): Promise<QuotesList> {
    const ws = await this.ensureConnected()

    const response = await ws.request<GetQuotesResponse>('GET_QUOTES', { symbols })

    // 转换响应格式为 QuotesList
    return {
      quotes: (response.quotes || []) as QuotesList['quotes'],
    }
  }

  // ==================== 账户数据 ====================

  /**
   * 获取现货账户信息
   *
   * @returns 现货账户信息
   */
  async getSpotAccount(): Promise<SpotAccountInfo> {
    const ws = await this.ensureConnected()

    const response = await ws.request<AccountDataResponse>('GET_SPOT_ACCOUNT')

    return response.account as SpotAccountInfo
  }

  /**
   * 获取期货账户信息
   *
   * @returns 期货账户信息
   */
  async getFuturesAccount(): Promise<FuturesAccountInfo> {
    const ws = await this.ensureConnected()

    const response = await ws.request<AccountDataResponse>('GET_FUTURES_ACCOUNT')

    return response.account as FuturesAccountInfo
  }

  // ==================== 告警管理 ====================

  /**
   * 获取告警配置列表
   *
   * @param page - 页码
   * @param pageSize - 每页数量
   * @returns 告警配置列表
   */
  async listAlertConfigs(page = 1, pageSize = 20): Promise<AlertConfig[]> {
    const ws = await this.ensureConnected()

    const response = await ws.request<AlertConfigResponse>('LIST_ALERT_CONFIGS', {
      page,
      pageSize,
    })

    // 后端返回 camelCase 格式
    return (response.items || []).map(item => {
      const rawItem = item as unknown as Record<string, unknown>
      return {
        ...item,
        // 兼容 snake_case 和 camelCase
        strategyType: (rawItem.strategyType as string) || (rawItem.strategy_type as string) || '',
        triggerType: (rawItem.triggerType as string) || (rawItem.trigger_type as string) || '',
        isEnabled: (rawItem.isEnabled as boolean) ?? (rawItem.is_enabled as boolean) ?? true,
        createdAt: (rawItem.createdAt as string) || (rawItem.created_at as string) || '',
        updatedAt: (rawItem.updatedAt as string) || (rawItem.updated_at as string) || '',
        createdBy: (rawItem.createdBy as string) || (rawItem.created_by as string) || undefined,
        params: this.convertParamsFromBackend(item.params),
      }
    })
  }

  /**
   * 获取单个告警配置
   *
   * @param id - 告警ID
   * @returns 告警配置
   */
  async getAlert(id: string): Promise<AlertConfig | null> {
    const ws = await this.ensureConnected()

    // GET_ALERT_CONFIG 后端未实现，暂时使用列表查询
    // TODO: 后端实现 GET_ALERT_CONFIG 后改为直接查询
    const response = await ws.request<AlertConfigResponse>('LIST_ALERT_CONFIGS', {
      limit: 1,
      offset: 0,
    })

    if (!response.items || response.items.length === 0) {
      return null
    }

    const alert = response.items[0]
    // 过滤参数值类型
    return {
      ...alert,
      params: this.convertParamsFromBackend(alert.params),
    }
  }

  /**
   * 创建告警配置
   *
   * @param config - 告警配置
   * @returns 创建的告警配置
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
    const ws = await this.ensureConnected()

    // 转换参数名称：前端使用简写，后端需要完整名称
    const params = this.convertParamsToBackend(config.params)

    const response = await ws.request<AlertConfigOperationResponse>('CREATE_ALERT_CONFIG', {
      // 生成 UUIDv4 hex 格式（32字符无短横线），与订单ID格式一致
      id: crypto.randomUUID().replace(/-/g, ''),
      name: config.name,
      description: config.description || '',
      strategyType: config.strategyType,
      symbol: config.symbol,
      interval: config.interval,
      triggerType: config.triggerType || 'each_kline_close',
      params,
      isEnabled: config.isEnabled ?? true,
      // 创建者标识，使用默认用户（个人项目）
      createdBy: 'local_user',
    })

    if (!response.id) {
      throw new Error('Failed to create alert')
    }

    // 后端已自动转换为驼峰命名，直接返回
    return {
      id: response.id,
      name: response.name || '',
      description: response.description || '',
      strategyType: response.strategyType || '',
      symbol: response.symbol || '',
      interval: response.interval || '',
      triggerType: response.triggerType || 'each_kline_close',
      params: this.convertParamsFromBackend(response.params),
      isEnabled: response.isEnabled ?? true,
      createdAt: response.createdAt,
      updatedAt: response.updatedAt,
    } as AlertConfig
  }

  /**
   * 更新告警配置
   *
   * @param id - 告警ID
   * @param updates - 更新内容
   * @returns 更新后的告警配置
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
    const ws = await this.ensureConnected()

    // 转换参数名称
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

    const response = await ws.request<AlertConfigOperationResponse>('UPDATE_ALERT_CONFIG', requestData)

    if (!response.id) {
      throw new Error('Failed to update alert')
    }

    // 后端已自动转换为驼峰命名，直接返回
    return {
      id: response.id,
      name: response.name || '',
      description: response.description || '',
      strategyType: response.strategyType || '',
      symbol: response.symbol || '',
      interval: response.interval || '',
      triggerType: response.triggerType || 'each_kline_close',
      params: this.convertParamsFromBackend(response.params),
      isEnabled: response.isEnabled ?? true,
      createdAt: response.createdAt,
      updatedAt: response.updatedAt,
    } as AlertConfig
  }

  /**
   * 删除告警配置
   *
   * @param id - 告警ID
   * @returns 是否删除成功
   */
  async deleteAlert(id: string): Promise<boolean> {
    const ws = await this.ensureConnected()

    await ws.request<{ success: boolean }>('DELETE_ALERT_CONFIG', { id })
    return true
  }

  /**
   * 启用告警
   * 使用 UPDATE_ALERT_CONFIG + isEnabled 字段实现
   *
   * @param id - 告警ID
   * @returns 启用结果
   */
  async enableAlert(id: string): Promise<{ id: string; isEnabled: boolean }> {
    const ws = await this.ensureConnected()

    const response = await ws.request<{ id: string; isEnabled: boolean }>('UPDATE_ALERT_CONFIG', {
      id,
      isEnabled: true,
    })

    return response
  }

  /**
   * 禁用告警
   * 使用 UPDATE_ALERT_CONFIG + isEnabled 字段实现
   *
   * @param id - 告警ID
   * @returns 禁用结果
   */
  async disableAlert(id: string): Promise<{ id: string; isEnabled: boolean }> {
    const ws = await this.ensureConnected()

    const response = await ws.request<{ id: string; isEnabled: boolean }>('UPDATE_ALERT_CONFIG', {
      id,
      isEnabled: false,
    })

    return response
  }

  /**
   * 批量订阅信号
   *
   * @param alertIds - 告警ID数组
   * @param callback - 信号回调
   * @returns 取消订阅函数
   */
  subscribeAllSignals(
    alertIds: string[],
    callback: (signal: SignalRecord) => void
  ): () => void {
    if (!this.wsClient) {
      throw new Error('DataService not connected. Call connect() first.')
    }

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

    // 返回批量取消订阅函数
    return () => {
      for (const unsub of unsubscribers) {
        unsub()
      }
      for (const alertId of alertIds) {
        this.subscriptionInfos.delete(`SIGNAL:${alertId}`)
      }
    }
  }

  // ==================== 参数转换 ====================

  /**
   * 将前端参数转换为后端API格式
   * 前端使用 snake_case 格式，直接传递给后端
   * 如果没有提供参数，返回 MACD 策略的默认值
   */
  private convertParamsToBackend(params?: Record<string, number | boolean>): Record<string, number | boolean> {
    // 默认参数使用 snake_case 格式
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

    // 返回前端传入的参数（已经是 snake_case 格式）
    return { ...params }
  }

  /**
   * 将后端返回的参数转换为前端格式
   * 保留 snake_case 键名，让前端表单可以动态渲染
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
   *
   * @param params - 查询参数
   * @returns 信号列表
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
    const ws = await this.ensureConnected()

    const response = await ws.request<SignalResponse>('LIST_SIGNALS', params || {})

    return response.items || []
  }

  // ==================== 订单管理 ====================

  /**
   * 获取订单列表
   *
   * @param params - 查询参数
   * @returns 订单列表
   */
  async listOrders(params?: {
    symbol?: string
    status?: string
    startTime?: number
    endTime?: number
    limit?: number
  }): Promise<OrderListData> {
    const ws = await this.ensureConnected()

    const response = await ws.request<OrderListResponseData>('LIST_ORDERS', params || {})

    return {
      orders: response.orders || [],
      count: response.count || 0,
    }
  }

  /**
   * 获取当前挂单
   *
   * @param symbol - 交易对（可选）
   * @returns 挂单列表
   */
  async getOpenOrders(symbol?: string): Promise<OrderListData> {
    const ws = await this.ensureConnected()

    const params = symbol ? { symbol } : {}
    const response = await ws.request<OrderListResponseData>('GET_OPEN_ORDERS', params)

    return {
      orders: response.orders || [],
      count: response.count || 0,
    }
  }

  // ==================== 策略元数据 ====================

  /**
   * 获取所有策略元数据列表
   *
   * @returns 策略元数据列表
   */
  async getStrategyMetadata(): Promise<StrategyMetadataResponse[]> {
    const ws = await this.ensureConnected()

    const response = await ws.request<StrategyMetadataListResponse>('GET_STRATEGY_METADATA')

    return response.strategies || []
  }

  /**
   * 获取指定策略的元数据
   *
   * @param strategyType - 策略类型（如 MACDResonanceStrategyV5）
   * @returns 策略元数据
   */
  async getStrategyMetadataByType(strategyType: string): Promise<StrategyMetadataResponse | null> {
    const ws = await this.ensureConnected()

    const response = await ws.request<{ strategy: StrategyMetadataResponse }>('GET_STRATEGY_METADATA_BY_TYPE', {
      strategyType,
    })

    return response.strategy || null
  }

  /**
   * 获取订单详情
   *
   * @param params - 查询参数
   * @returns 订单详情
   */
  async getOrder(params: { symbol: string; orderId?: number; origClientOrderId?: string }): Promise<Order> {
    const ws = await this.ensureConnected()

    const response = await ws.request<OrderResponse>('GET_ORDER', params)

    return response.order
  }

  // ==================== 订阅管理 ====================

  /**
   * 订阅实时数据
   *
   * @param subscriptionKey - 订阅键
   * @param handler - 数据回调
   * @returns 取消订阅函数
   */
  subscribe(subscriptionKey: string, handler: (data: unknown, subscriptionKey?: string) => void): () => void {
    if (!this.wsClient) {
      throw new Error('DataService not connected. Call connect() first.')
    }
    return this.wsClient.subscribe(subscriptionKey, handler)
  }

  /**
   * 取消订阅
   *
   * @param subscriptionKey - 订阅键
   */
  unsubscribe(subscriptionKey: string): void {
    this.wsClient?.unsubscribe(subscriptionKey)
    this.subscriptionInfos.delete(subscriptionKey)
  }

  /**
   * 获取当前所有订阅
   *
   * @returns 订阅键数组
   */
  getSubscriptions(): string[] {
    return this.wsClient?.getSubscriptions() || []
  }

  // ==================== 类型安全订阅方法 ====================

  /**
   * 订阅K线实时数据
   *
   * @param symbol - 交易对 (如 'BINANCE:BTCUSDT')
   * @param interval - K线周期 (如 '1', '5', '60', '1D')
   * @param callback - 数据回调
   * @param options - 订阅选项
   * @returns 取消订阅函数
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
   *
   * @param symbols - 交易对列表
   * @param callback - 数据回调 (接收Map格式，key为symbol)
   * @param options - 订阅选项
   * @returns 取消订阅函数
   */
  subscribeQuotes(
    symbols: string[],
    callback: (quotes: Map<string, QuotesValue>) => void,
    options?: SubscriptionOptions
  ): () => void {
    const finalOptions: SubscriptionOptions = { reconnect: true, ...options }
    const quotesMap = new Map<string, QuotesValue>()

    // 收集所有 subscriptionKeys 和 handlers
    const subscriptionKeys: string[] = []
    const handlersMap = new Map<string, (data: unknown) => void>()

    for (const symbol of symbols) {
      const subscriptionKey = `${symbol}@QUOTES`
      subscriptionKeys.push(subscriptionKey)

      // 构建 handler
      const handler = (data: unknown) => {
        const quoteData = data as QuotesValue
        quotesMap.set(symbol, quoteData)
        callback(new Map(quotesMap))
      }
      handlersMap.set(subscriptionKey, handler)

      // 存储订阅信息
      this.subscriptionInfos.set(subscriptionKey, {
        key: subscriptionKey,
        callback: handler as SubscriptionCallback<unknown>,
        options: finalOptions,
        subscribedAt: Date.now(),
        status: 'active',
      })
    }

    // 一次性订阅（WSClient 会将所有 keys 放入一个数组发送）
    const unsubscribe = this.wsClient!.subscribe(subscriptionKeys, handlersMap)

    // 返回批量取消订阅函数
    return () => {
      unsubscribe()
      // 清理订阅信息
      for (const symbol of symbols) {
        this.subscriptionInfos.delete(`${symbol}@QUOTES`)
      }
    }
  }

  /**
   * 订阅账户增量更新
   *
   * 注意：账户订阅需要先GET初始化数据，再订阅增量更新
   *
   * @param accountType - 账户类型 'SPOT' | 'FUTURES'
   * @param callback - 数据回调
   * @param options - 订阅选项
   * @returns 取消订阅函数
   */
  subscribeAccount(
    accountType: 'SPOT' | 'FUTURES',
    callback: (update: AccountUpdate) => void,
    options?: SubscriptionOptions
  ): () => void {
    const subscriptionKey = `BINANCE:ACCOUNT@${accountType}`
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
   *
   * @param alertId - 告警ID
   * @param callback - 数据回调
   * @param options - 订阅选项
   * @returns 取消订阅函数
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

  // ==================== 订阅信息管理 ====================

  /**
   * 获取订阅信息
   *
   * @param subscriptionKey - 订阅键
   * @returns 订阅信息
   */
  getSubscriptionInfo(subscriptionKey: string): SubscriptionInfo | undefined {
    return this.subscriptionInfos.get(subscriptionKey)
  }

  /**
   * 获取所有订阅信息
   *
   * @returns 订阅信息数组
   */
  getAllSubscriptionInfos(): SubscriptionInfo[] {
    return Array.from(this.subscriptionInfos.values())
  }

  /**
   * 清空所有订阅信息
   */
  clearSubscriptions(): void {
    // 取消所有WS订阅
    for (const key of this.subscriptionInfos.keys()) {
      this.wsClient?.unsubscribe(key)
    }
    this.subscriptionInfos.clear()
  }

  // ==================== 批量订阅 ====================

  /**
   * 批量订阅 (遵循协议: 50个/包, 250ms间隔)
   *
   * @param subscriptions - 订阅配置数组
   * @returns 取消所有订阅的函数
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
