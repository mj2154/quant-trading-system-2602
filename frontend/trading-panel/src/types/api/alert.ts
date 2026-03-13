/**
 * 告警类型 - 对应后端 alert_config_models.py
 *
 * 使用 camelCase 与 WebSocket 协议保持一致
 * 后端使用 SnakeCaseModel 接收请求，CamelCaseModel 返回响应
 */

// ==================== 告警枚举类型 ====================

/**
 * 告警触发类型
 * - once_only: 仅一次触发
 * - each_kline: 每根K线触发
 * - each_kline_close: 每根K线收盘触发
 * - each_minute: 每分钟触发
 */
export type AlertTriggerType =
  | 'once_only'
  | 'each_kline'
  | 'each_kline_close'
  | 'each_minute'

/**
 * 告警策略类型
 * 支持设计文档中定义的所有策略类型
 */
export type AlertStrategyType =
  | 'macd'
  | 'random'
  | 'MACDResonanceStrategyV5'
  | 'MACDResonanceStrategyV6'
  | 'MACDResonanceShortStrategy'
  | 'Alpha01Strategy'

// ==================== 请求模型 ====================

/**
 * 创建告警信号请求
 *
 * 对应后端 AlertSignalCreate / CreateAlertSignalRequest
 */
export interface CreateAlertSignalRequest {
  /** 告警ID（UUID格式，由前端生成） */
  id: string
  /** 告警名称 */
  name: string
  /** 告警描述（可选） */
  description?: string
  /** 策略类型 */
  strategyType: string
  /** 交易品种 */
  symbol: string
  /** K线周期 */
  interval: string
  /** 触发类型 */
  triggerType: string
  /** 策略参数 */
  params?: Record<string, unknown>
  /** 是否启用（默认true） */
  isEnabled?: boolean
  /** 创建人 */
  createdBy?: string
}

/**
 * 更新告警信号请求
 *
 * 对应后端 AlertSignalUpdate / UpdateAlertSignalRequest
 * 所有字段可选，用于部分更新
 */
export interface UpdateAlertSignalRequest {
  /** 告警名称 */
  name?: string
  /** 告警描述 */
  description?: string
  /** 策略类型 */
  strategyType?: string
  /** 交易品种 */
  symbol?: string
  /** K线周期 */
  interval?: string
  /** 触发类型 */
  triggerType?: string
  /** 策略参数 */
  params?: Record<string, unknown>
  /** 是否启用 */
  isEnabled?: boolean
}

/**
 * 删除告警信号请求
 *
 * 对应后端 DeleteAlertSignalRequest
 */
export interface DeleteAlertSignalRequest {
  /** 告警信号ID */
  id: string
}

/**
 * 启用/禁用告警请求
 *
 * 对应后端 EnableAlertSignalRequest
 */
export interface EnableAlertSignalRequest {
  /** 告警信号ID */
  id: string
  /** 是否启用 */
  isEnabled: boolean
}

/**
 * 查询告警列表请求
 *
 * 对应后端 ListAlertSignalsRequest
 */
export interface ListAlertSignalsRequest {
  /** 最大记录数 */
  limit?: number
  /** 偏移量 */
  offset?: number
  /** 按启用状态筛选 */
  isEnabled?: boolean
  /** 按交易对筛选 */
  symbol?: string
  /** 按策略类型筛选 */
  strategyType?: string
}

// ==================== 响应模型 ====================

/**
 * 告警信号响应
 *
 * 对应后端 AlertSignalResponse
 */
export interface AlertSignalResponse {
  /** 告警信号ID */
  id: string
  /** 告警名称 */
  name: string
  /** 告警描述 */
  description?: string
  /** 策略类型 */
  strategyType: string
  /** 交易品种 */
  symbol: string
  /** K线周期 */
  interval: string
  /** 触发类型 */
  triggerType: string
  /** 策略参数 */
  params: Record<string, unknown>
  /** 是否启用 */
  isEnabled: boolean
  /** 创建时间 */
  createdAt: string
  /** 最后更新时间 */
  updatedAt: string
  /** 创建人 */
  createdBy?: string
}

/**
 * 告警信号列表响应
 *
 * 对应后端 AlertSignalListResponse
 */
export interface AlertSignalListResponse {
  /** 告警数组 */
  items: AlertSignalResponse[]
  /** 总数 */
  total: number
  /** 当前页码 */
  page: number
  /** 每页数量 */
  pageSize: number
}

/**
 * 启用/禁用响应
 *
 * 对应后端 EnableDisableResponse
 */
export interface EnableDisableAlertResponse {
  /** 告警信号ID */
  id: string
  /** 告警名称 */
  name: string
  /** 是否启用 */
  isEnabled: boolean
  /** 操作结果消息 */
  message: string
}

// ==================== 兼容类型（前端展示用） ====================

/**
 * 告警配置（兼容现有代码）
 */
export interface AlertConfig extends AlertSignalResponse {}

/**
 * 告警配置列表响应（兼容现有代码）
 */
export interface AlertConfigListResponse extends AlertSignalListResponse {}

/**
 * MACD 参数配置
 */
export interface AlertMacdParams {
  fast1: number
  slow1: number
  signal1: number
  fast2: number
  slow2: number
  signal2: number
}

/**
 * 告警参数配置
 */
export interface AlertParams {
  /** MACD快速周期 */
  fastPeriod?: number
  /** MACD慢速周期 */
  slowPeriod?: number
  /** MACD信号线周期 */
  signalPeriod?: number
  /** 阈值设置 */
  threshold?: number
  /** 策略特定参数 */
  [key: string]: unknown
}

// ==================== 常量定义 ====================

/**
 * 触发类型选项
 */
export const ALERT_TRIGGER_TYPE_OPTIONS: { label: string; value: AlertTriggerType }[] = [
  { label: '仅一次 (once_only)', value: 'once_only' },
  { label: '每根K线 (each_kline)', value: 'each_kline' },
  { label: '每根K线收盘 (each_kline_close)', value: 'each_kline_close' },
  { label: '每分钟 (each_minute)', value: 'each_minute' },
]

/**
 * 策略类型选项
 */
export const ALERT_STRATEGY_TYPE_OPTIONS: { label: string; value: AlertStrategyType }[] = [
  { label: 'MACD共振策略V5', value: 'MACDResonanceStrategyV5' },
  { label: 'MACD共振策略V6', value: 'MACDResonanceStrategyV6' },
  { label: 'MACD做空策略', value: 'MACDResonanceShortStrategy' },
  { label: 'Alpha01策略', value: 'Alpha01Strategy' },
  { label: 'MACD策略 (macd)', value: 'macd' },
  { label: '随机策略 (random)', value: 'random' },
]

/**
 * K线周期选项
 */
export const INTERVAL_OPTIONS: { label: string; value: string }[] = [
  { label: '1分钟', value: '1' },
  { label: '5分钟', value: '5' },
  { label: '15分钟', value: '15' },
  { label: '1小时', value: '60' },
  { label: '4小时', value: '240' },
  { label: '日线', value: 'D' },
  { label: '周线', value: 'W' },
]

/**
 * 交易对选项
 */
export const SYMBOL_OPTIONS: { label: string; value: string }[] = [
  { label: 'BTC/USDT', value: 'BINANCE:BTCUSDT' },
  { label: 'ETH/USDT', value: 'BINANCE:ETHUSDT' },
  { label: 'BNB/USDT', value: 'BINANCE:BNBUSDT' },
  { label: 'SOL/USDT', value: 'BINANCE:SOLUSDT' },
  { label: 'XRP/USDT', value: 'BINANCE:XRPUSDT' },
  { label: 'ADA/USDT', value: 'BINANCE:ADAUSDT' },
  { label: 'DOGE/USDT', value: 'BINANCE:DOGEUSDT' },
  { label: 'AVAX/USDT', value: 'BINANCE:AVAXUSDT' },
  { label: 'DOT/USDT', value: 'BINANCE:DOTUSDT' },
  { label: 'MATIC/USDT', value: 'BINANCE:MATICUSDT' },
]
