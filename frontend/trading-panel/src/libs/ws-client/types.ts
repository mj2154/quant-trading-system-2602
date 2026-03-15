/**
 * 统一WebSocket客户端 - 类型定义
 *
 * 严格遵循 WS协议 v2.0 设计文档
 * 文档: docs/backend/design/07-websocket-protocol.md
 */

import type {
  SpotAccountInfo,
  FuturesAccountInfo,
  AlertConfig,
  SignalRecord,
  Order,
  OrderListResponse,
  CreateOrderParams,
} from '../../types'

// ==================== 协议基础类型 ====================

/** 协议版本 */
export const PROTOCOL_VERSION = '2.0'

/** 请求超时默认时间 (毫秒) */
export const DEFAULT_REQUEST_TIMEOUT = 30000

/** 重连间隔 (毫秒) */
export const DEFAULT_RECONNECT_INTERVAL = 3000

// ==================== 消息类型 ====================

/** 客户端请求类型 */
export type ClientRequestType =
  | 'GET_KLINES'
  | 'GET_QUOTES'
  | 'GET_CONFIG'
  | 'GET_SERVER_TIME'
  | 'GET_SEARCH_SYMBOLS'
  | 'GET_RESOLVE_SYMBOL'
  | 'GET_SUBSCRIPTIONS'
  | 'GET_SPOT_ACCOUNT'
  | 'GET_FUTURES_ACCOUNT'
  | 'SUBSCRIBE'
  | 'UNSUBSCRIBE'
  | 'CREATE_ALERT_CONFIG'
  | 'GET_ALERT_CONFIG'
  | 'LIST_ALERT_CONFIGS'
  | 'UPDATE_ALERT_CONFIG'
  | 'DELETE_ALERT_CONFIG'
  | 'LIST_SIGNALS'
  | 'CREATE_ORDER'
  | 'GET_ORDER'
  | 'LIST_ORDERS'
  | 'CANCEL_ORDER'
  | 'GET_OPEN_ORDERS'
  | 'GET_STRATEGY_METADATA'
  | 'GET_STRATEGY_METADATA_BY_TYPE'

/** 服务端响应类型 */
export type ServerResponseType =
  | 'ACK'
  | 'KLINES_DATA'
  | 'QUOTES_DATA'
  | 'CONFIG_DATA'
  | 'SERVER_TIME_DATA'
  | 'SEARCH_SYMBOLS_DATA'
  | 'SYMBOL_DATA'
  | 'SUBSCRIPTION_DATA'
  | 'ACCOUNT_DATA'
  | 'ALERT_CONFIG_DATA'
  | 'SIGNAL_DATA'
  | 'ORDER_DATA'
  | 'ORDER_LIST_DATA'
  | 'ORDER_UPDATE'
  | 'STRATEGY_METADATA_DATA'
  | 'ERROR'

/** 推送类型 */
export type PushType = 'UPDATE' | 'ORDER_UPDATE'

// ==================== 消息结构 ====================

/** WebSocket消息基础结构 */
export interface WSMessage {
  protocolVersion: string
  type: string
  requestId?: string
  timestamp: number
  data?: unknown
}

/** 客户端请求消息 */
export interface WSRequestMessage extends WSMessage {
  type: ClientRequestType
  requestId: string
  data?: Record<string, unknown>
}

/** 服务端响应消息 */
export interface WSResponseMessage extends WSMessage {
  type: ServerResponseType
  requestId: string
}

// ==================== 客户端配置 ====================

/** WS客户端配置选项 */
export interface WSClientOptions {
  /** WebSocket服务器URL */
  url: string
  /** 是否自动重连 */
  autoReconnect?: boolean
  /** 重连间隔 (毫秒) */
  reconnectInterval?: number
  /** 请求超时时间 (毫秒) */
  requestTimeout?: number
  /** 连接成功回调 */
  onConnect?: () => void
  /** 断开连接回调 */
  onDisconnect?: () => void
  /** 错误回调 */
  onError?: (error: Error) => void
  /** 消息回调 (所有消息) */
  onMessage?: (message: WSMessage) => void
}

/** WS客户端默认配置 */
export const DEFAULT_WS_CLIENT_OPTIONS: Required<WSClientOptions> = {
  url: 'ws://localhost:8000/ws',
  autoReconnect: true,
  reconnectInterval: DEFAULT_RECONNECT_INTERVAL,
  requestTimeout: DEFAULT_REQUEST_TIMEOUT,
  onConnect: () => {},
  onDisconnect: () => {},
  onError: () => {},
  onMessage: () => {},
}

// ==================== 请求响应类型 ====================

/** 待处理的请求 */
export interface PendingRequest<T = unknown> {
  resolve: (value: T) => void
  reject: (reason: Error) => void
  timeoutId: number
}

/** 订阅者回调 */
export type SubscriptionHandler = (data: unknown, subscriptionKey?: string) => void

/** 订阅者信息 */
export interface Subscription {
  key: string
  handler: SubscriptionHandler
}

// ==================== API响应类型 ====================

/** K线数据响应 - 与 datafeed.js 保持一致 */
export interface GetKlinesResponse {
  symbol: string
  interval: string
  bars: Array<{
    time: number
    open: number
    high: number
    low: number
    close: number
    volume: number
  }>
  count: number
  noData: boolean
  nextTime?: number
  type?: string
}

/** 报价数据响应 - 与 datafeed.js 保持一致，使用嵌套结构 */
export interface GetQuotesResponse {
  type?: string
  quotes: Array<{
    n: string     // symbol name
    s: string     // status
    v: {         // values
      ch: number       // change
      lp: number       // last price
      chp: number      // change percent
      low?: number
      high?: number
      volume?: number
      quote_volume?: number
      timestamp?: number
    }
  }>
  count: number
}

/** 账户数据响应 */
export interface AccountDataResponse {
  account: SpotAccountInfo | FuturesAccountInfo
  accountType: 'spot' | 'futures'
}

/** 订单响应 */
export interface OrderResponse {
  order: Order
}

/** 订单列表响应 */
export interface OrderListResponseData {
  orders: Order[]
  count: number
}

/** 告警配置响应 - 对应后端 handle_list_alert_configs 返回的 data 字段（后端使用 CamelCaseModel 自动转换） */
export interface AlertConfigResponse {
  type: string
  items: AlertConfig[]
  total: number
  page: number
  pageSize: number
}

/** 告警配置操作响应 - 对应后端 create/update/delete/enable/disable 操作返回的 data 字段（后端使用 CamelCaseModel 自动转换） */
export interface AlertConfigOperationResponse {
  type: string
  id: string
  message?: string
  name?: string
  description?: string
  strategyType?: string
  symbol?: string
  interval?: string
  triggerType?: string
  params?: Record<string, unknown>
  isEnabled?: boolean
  createdAt?: string
  updatedAt?: string
}

/** 信号响应 - 对应后端 handle_list_signals 返回的 data 字段（后端使用 CamelCaseModel 自动转换） */
export interface SignalResponse {
  type: string
  items: SignalRecord[]
  total: number
  page: number
  pageSize: number
}

/** 订阅响应 - 对应后端 SubscribeData */
export interface SubscriptionResponse {
  status: string
  subscriptions: string[]
  failed?: Array<{
    subscriptionKey: string
    reason: string
  }>
}

/** 订阅列表响应 - 对应后端 SubscriptionsData */
export interface SubscriptionsResponse {
  type: string
  subscriptions: Array<{
    subscriptionKey: string
    dataType: string
    exchange: string
    symbol: string
    interval?: string
    productType: string
    status: string
    subscribedAt: number
    messageCount: number
    lastMessageAt?: number
  }>
  total: number
  activeCount: number
  inactiveCount: number
}

/** 配置响应 - 对应后端 ConfigData */
export interface ConfigResponse {
  supportsSearch: boolean
  supportsGroupRequest: boolean
  supportsMarks: boolean
  supportsTimescaleMarks: boolean
  supportsTime: boolean
  supportedResolutions: string[]
  currencyCodes: string[]
  symbolsTypes: Array<{
    name: string
    value: string
  }>
}

/** 搜索响应 - 对应后端 SearchSymbolsData */
export interface SearchSymbolsResponse {
  symbols: Array<{
    symbol: string
    fullName: string
    description: string
    exchange: string
    ticker: string
    type: string
  }>
  total: number
  count: number
}

/** 指标响应 - 对应后端 MetricsData */
export interface MetricsResponse {
  type: string
  metrics: {
    pendingTasks: number
    connectedClients: number
  }
  activeConnections: number
  subscriptionCount: number
}

/** 服务器时间响应 - 对应后端 ServerTimeData */
export interface ServerTimeResponse {
  serverTime: number
  timezone: string
}

/** 策略参数定义 - 对应后端 StrategyParam */
export interface StrategyParamResponse {
  name: string
  type: string
  default: number | boolean
  min?: number
  max?: number
  description: string
}

/** 策略元数据 - 对应后端 StrategyMetadataResponse */
export interface StrategyMetadataResponse {
  type: string
  name: string
  description: string
  params: StrategyParamResponse[]
  createdAt?: string
  updatedAt?: string
}

/** 策略元数据列表响应 - 对应后端 StrategyMetadataListResponse */
export interface StrategyMetadataListResponse {
  strategies: StrategyMetadataResponse[]
}

/** 策略元数据单个响应 - GET_STRATEGY_METADATA_BY_TYPE 返回 */
export interface StrategyMetadataSingleResponse {
  strategy: StrategyMetadataResponse
}

// ==================== 客户端接口 ====================

/** 统一WS客户端接口 */
export interface IWSClient {
  /** 连接状态 */
  readonly isConnected: boolean
  /** 连接 */
  connect(): Promise<void>
  /** 断开连接 */
  disconnect(): void
  /** 发送请求并等待响应 */
  request<T>(type: ClientRequestType, data?: Record<string, unknown>): Promise<T>
  /** 订阅实时数据 */
  subscribe(subscriptionKey: string, handler: SubscriptionHandler): () => void
  /** 取消订阅 */
  unsubscribe(subscriptionKey: string): void
  /** 获取所有订阅 */
  getSubscriptions(): string[]
}

// ==================== API函数类型 ====================

/** API调用函数类型 */
export type APICallFunction = <T>(data?: Record<string, unknown>) => Promise<T>

/** API集合 */
export interface WSClientAPI {
  // 市场数据
  getKlines: (symbol: string, interval: string, fromTime: number, toTime: number, limit?: number) => Promise<GetKlinesResponse>
  getQuotes: (symbols: string[]) => Promise<GetQuotesResponse>

  // 账户数据
  getSpotAccount: () => Promise<AccountDataResponse>
  getFuturesAccount: () => Promise<AccountDataResponse>

  // 交易操作
  createOrder: (params: CreateOrderParams) => Promise<OrderResponse>
  getOrder: (params: { symbol: string; orderId?: number; origClientOrderId?: string }) => Promise<OrderResponse>
  listOrders: (filters?: Record<string, unknown>) => Promise<OrderListResponseData>
  cancelOrder: (params: { symbol: string; orderId?: number; origClientOrderId?: string }) => Promise<OrderResponse>
  getOpenOrders: (symbol?: string) => Promise<OrderResponse>

  // 告警管理
  listAlertConfigs: (page?: number, pageSize?: number) => Promise<AlertConfigResponse>
  getAlertConfig: (id: string) => Promise<AlertConfigResponse>
  createAlertConfig: (config: Record<string, unknown>) => Promise<AlertConfigResponse>
  updateAlertConfig: (id: string, updates: Record<string, unknown>) => Promise<AlertConfigResponse>
  deleteAlertConfig: (id: string) => Promise<void>
  enableAlertConfig: (id: string) => Promise<AlertConfigResponse>
  disableAlertConfig: (id: string) => Promise<AlertConfigResponse>

  // 信号
  listSignals: (filters?: Record<string, unknown>) => Promise<SignalResponse>

  // 订阅管理
  subscribe: (key: string, handler: SubscriptionHandler) => () => void
  unsubscribe: (key: string) => void
  getSubscriptions: () => string[]
}
