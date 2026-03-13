/**
 * 信号数据类型 - 对应后端 signal_models.py
 *
 * 使用 camelCase 与 WebSocket 协议保持一致
 * 后端使用 CamelCaseModel 序列化，自动转为 camelCase
 */

// ==================== 策略参数 ====================

/**
 * 策略参数定义
 *
 * 对应后端 StrategyParam
 */
export interface StrategyParam {
  /** 参数名称 */
  name: string
  /** 参数类型 */
  type: string
  /** 默认值 */
  default: number | boolean
  /** 最小值 */
  min?: number
  /** 最大值 */
  max?: number
  /** 参数描述 */
  description: string
}

/**
 * 策略元数据
 *
 * 对应后端 StrategyMetadataResponse
 */
export interface StrategyMetadata {
  /** 策略类型（类名） */
  type: string
  /** 策略显示名称 */
  name: string
  /** 策略描述 */
  description: string
  /** 策略参数列表 */
  params: StrategyParam[]
  /** 创建时间 */
  createdAt?: string
  /** 更新时间 */
  updatedAt?: string
}

/**
 * 策略元数据列表响应
 *
 * 对应后端 StrategyMetadataListResponse
 */
export interface StrategyMetadataListResponse {
  /** 策略元数据列表 */
  strategies: StrategyMetadata[]
}

// ==================== 信号记录 ====================

/**
 * 信号记录响应
 *
 * 对应后端 SignalRecordResponse
 * 用于 LIST_SIGNALS 响应
 */
export interface SignalRecord {
  /** 信号数据库自增ID */
  id: number
  /** 关联的告警配置ID (UUID) */
  alertId: string
  /** 关联的配置ID（可选） */
  configId?: string
  /** 策略名称 */
  strategyType: string
  /** 交易对 */
  symbol: string
  /** K线周期 */
  interval: string
  /** 触发类型 */
  triggerType?: string
  /** 信号值: true=做多, false=做空, null=无信号 */
  signalValue?: boolean | null
  /** 信号原因 */
  signalReason?: string | null
  /** 信号计算时间 */
  computedAt: string
  /** 触发该信号的订阅键 */
  sourceSubscriptionKey?: string
  /** 附加元数据 */
  metadata: Record<string, unknown>
}

/**
 * 信号列表响应
 *
 * 对应后端 SignalListResponse
 */
export interface SignalListResponse {
  /** 信号记录列表 */
  items: SignalRecord[]
  /** 总数量 */
  total: number
  /** 当前页码 */
  page: number
  /** 每页数量 */
  pageSize: number
}

// ==================== 查询参数 ====================

/**
 * 信号记录查询参数
 */
export interface SignalRecordQueryParams {
  /** 页码 */
  page?: number
  /** 每页数量 */
  pageSize?: number
  /** 交易品种筛选 */
  symbol?: string
  /** 策略类型筛选 */
  strategyType?: string
  /** K线周期筛选 */
  interval?: number | string
  /** 信号值筛选 */
  signalValue?: boolean
  /** 创建者筛选 */
  createdBy?: string
  /** 起始时间戳（毫秒） */
  fromTime?: number
  /** 结束时间戳（毫秒） */
  toTime?: number
  /** 排序字段 */
  orderBy?: string
  /** 排序方向 */
  orderDir?: 'asc' | 'desc'
}

// ==================== 响应类型 ====================

/**
 * 启用/禁用响应
 */
export interface EnableDisableResponse {
  /** 配置ID */
  id: string
  /** 名称 */
  name: string
  /** 是否启用 */
  isEnabled: boolean
  /** 操作结果消息 */
  message: string
}
