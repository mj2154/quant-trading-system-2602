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
  type SignalResponse,
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

    return response.configs || []
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

    return response.signals || []
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
    const unsubscribers: Array<() => void> = []
    const quotesMap = new Map<string, QuotesValue>()

    // 为每个交易对创建订阅
    for (const symbol of symbols) {
      const subscriptionKey = `${symbol}@QUOTES`

      this.subscriptionInfos.set(subscriptionKey, {
        key: subscriptionKey,
        callback: ((data: unknown) => {
          const quoteData = data as QuotesValue
          quotesMap.set(symbol, quoteData)
          callback(new Map(quotesMap))
        }) as SubscriptionCallback<unknown>,
        options: finalOptions,
        subscribedAt: Date.now(),
        status: 'active',
      })

      const unsub = this.subscribe(subscriptionKey, (data, sk) => {
        const quoteData = data as QuotesValue
        quotesMap.set(symbol, quoteData)
        callback(new Map(quotesMap))
      })
      unsubscribers.push(unsub)
    }

    // 返回批量取消订阅函数
    return () => {
      for (const unsub of unsubscribers) {
        unsub()
      }
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
