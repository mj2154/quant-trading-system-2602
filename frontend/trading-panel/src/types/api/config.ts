/**
 * 配置与搜索数据类型定义
 *
 * 对应后端 services/api-service/src/models/protocol/ws_payload.py
 * 使用 camelCase 与 WebSocket 协议保持一致
 */

// ==================== 配置类型 ====================

/**
 * TradingView 标的类型
 * 对应后端 SymbolType
 */
export interface SymbolType {
  /** 显示名称 */
  name: string
  /** 值 */
  value: string
}

/**
 * 数据源配置响应
 * 对应后端 ConfigData
 */
export interface ConfigData {
  /** 支持搜索 */
  supportsSearch: boolean
  /** 支持分组请求 */
  supportsGroupRequest: boolean
  /** 支持标记 */
  supportsMarks: boolean
  /** 支持时间轴标记 */
  supportsTimescaleMarks: boolean
  /** 支持时间 */
  supportsTime: boolean
  /** 支持的分辨率 */
  supportedResolutions: string[]
  /** 支持的货币代码 */
  currencyCodes: string[]
  /** 标的类型列表 */
  symbolsTypes: SymbolType[]
}

// ==================== 搜索类型 ====================

/**
 * 搜索结果中的单个交易对项
 * 对应后端 SymbolSearchItem
 */
export interface SymbolSearchItem {
  /** 标的全名（格式：EXCHANGE:SYMBOL） */
  symbol: string
  /** 标的全名（与 symbol 相同） */
  fullName: string
  /** 标的描述 */
  description: string
  /** 交易所 */
  exchange: string
  /** 交易代码 */
  ticker: string
  /** 标的类型 */
  type: string
}

/**
 * 搜索响应数据载荷
 * 对应后端 SearchSymbolsData
 */
export interface SearchSymbolsData {
  /** 交易对列表 */
  symbols: SymbolSearchItem[]
  /** 总数量 */
  total: number
  /** 当前返回数量 */
  count: number
}

// ==================== 订阅类型 ====================

/**
 * 单个订阅信息
 * 对应后端 SubscriptionItem
 */
export interface SubscriptionItem {
  /** 订阅键（v2.0格式） */
  subscriptionKey: string
  /** 数据类型（kline/quotes/trade） */
  dataType: string
  /** 交易所代码 */
  exchange: string
  /** 交易对代码 */
  symbol: string
  /** 分辨率（如适用） */
  interval?: string
  /** 产品类型（spot/perpetual/quarterly） */
  productType: string
  /** 订阅状态（active/inactive/error） */
  status: string
  /** 订阅时间戳 */
  subscribedAt: number
  /** 接收到的消息数量 */
  messageCount: number
  /** 最后一条消息时间戳 */
  lastMessageAt?: number
}

/**
 * 失败的订阅项
 * 对应后端 FailedSubscription
 */
export interface FailedSubscription {
  /** 订阅键 */
  subscriptionKey: string
  /** 失败原因 */
  reason: string
}

/**
 * 订阅列表响应数据载荷
 * 对应后端 SubscriptionsData
 */
export interface SubscriptionsData {
  /** 数据类型 */
  type: string
  /** 订阅列表 */
  subscriptions: SubscriptionItem[]
  /** 总订阅数 */
  total: number
  /** 活跃订阅数 */
  activeCount: number
  /** 非活跃订阅数 */
  inactiveCount: number
}

/**
 * 订阅响应（用于 SUBSCRIBE/UNSUBSCRIBE 确认）
 */
export interface SubscribeData {
  /** 状态：success/partial */
  status: string
  /** 成功的订阅键列表 */
  subscriptions: string[]
  /** 失败的订阅列表 */
  failed?: FailedSubscription[]
}

// ==================== 指标类型 ====================

/**
 * 系统指标数据
 * 对应后端 SystemMetrics
 */
export interface SystemMetrics {
  /** 待处理任务数 */
  pendingTasks: number
  /** 活跃连接数 */
  connectedClients: number
}

/**
 * 指标响应数据载荷
 * 对应后端 MetricsData
 */
export interface MetricsData {
  /** 数据类型 */
  type: string
  /** 指标数据 */
  metrics: SystemMetrics
  /** 活跃连接数（冗余，为兼容性） */
  activeConnections: number
  /** 订阅数量（冗余，为兼容性） */
  subscriptionCount: number
}

// ==================== 服务器时间类型 ====================

/**
 * 服务器时间数据载荷
 * 对应后端 ServerTimeData
 */
export interface ServerTimeData {
  /** 服务器时间 */
  serverTime: number
  /** 时区 */
  timezone: string
}
