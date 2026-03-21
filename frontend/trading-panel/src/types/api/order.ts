/**
 * 订单数据类型 - 对应后端 order_models.py
 *
 * 使用 camelCase 与 WebSocket 协议保持一致
 * 后端使用 SnakeCaseModel 接收请求，CamelCaseModel 返回响应
 *
 * 设计原则：
 * - 前端不区分期货/现货创建订单请求，通过 symbol 前缀自动识别
 * - 后端根据 symbol 前缀区分期货/现货，使用对应的请求模型验证
 * - 响应数据统一格式
 *
 * v2.0 设计变更：
 * - 移除 marketType 字段，通过 symbol 前缀区分市场类型
 *   - 现货：BINANCE:BTCUSDT
 *   - 期货：BINANCE:BTCUSDT.PERP
 */

// ==================== 枚举类型 ====================

/** 订单方向 */
export type OrderSide = 'BUY' | 'SELL'

/** 订单类型（期货）
 *
 * LIMIT, MARKET, STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET, TRAILING_STOP_MARKET
 */
export type FuturesOrderType =
  | 'LIMIT'
  | 'MARKET'
  | 'STOP'
  | 'STOP_MARKET'
  | 'TAKE_PROFIT'
  | 'TAKE_PROFIT_MARKET'
  | 'TRAILING_STOP_MARKET'

/** 订单类型（现货）
 *
 * LIMIT, MARKET, LIMIT_MAKER, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT, TRAILING_STOP_MARKET
 */
export type SpotOrderType =
  | 'LIMIT'
  | 'MARKET'
  | 'LIMIT_MAKER'
  | 'STOP_LOSS'
  | 'STOP_LOSS_LIMIT'
  | 'TAKE_PROFIT'
  | 'TAKE_PROFIT_LIMIT'
  | 'TRAILING_STOP_MARKET'

/** 订单有效时间
 *
 * 注意：GTX, GTD, RPI 仅期货支持
 */
export type OrderTimeInForce = 'GTC' | 'IOC' | 'FOK' | 'GTX' | 'GTD' | 'RPI'

/** 订单状态 */
export type OrderStatus =
  | 'NEW'
  | 'PARTIALLY_FILLED'
  | 'FILLED'
  | 'CANCELED'
  | 'PENDING_CANCEL'
  | 'REJECTED'
  | 'EXPIRED'

/** 持仓方向（仅期货） */
export type PositionSide = 'BOTH' | 'LONG' | 'SHORT'

/** 订单类型（通用） */
export type OrderType = FuturesOrderType | SpotOrderType

// ==================== 期货订单请求模型 ====================

/**
 * 期货创建订单请求
 *
 * 对应后端 FuturesCreateOrderRequest
 * 严格遵循官方期货 API 文档设计
 *
 * 注意：
 * - 期货不支持：activationPrice, workingType, priceProtect, closePosition
 * - 期货支持：position_side, reduce_only, callback_rate, price_match, good_till_date
 */
export interface FuturesCreateOrderRequest {
  /** 交易对符号（必填），如 BTCUSDT */
  symbol: string
  /** 订单方向：BUY 或 SELL */
  side: OrderSide
  /** 订单类型 */
  type: FuturesOrderType
  /** 订单数量，必须大于0 */
  quantity: number
  /** 客户端订单ID（可选，币安自动生成） */
  newClientOrderId?: string
  /** 持仓方向：BOTH, LONG, SHORT（对冲模式必填） */
  positionSide?: PositionSide
  /** 限价价格（LIMIT 订单必填） */
  price?: number
  /** 订单有效时间：GTC, IOC, FOK, GTD（LIMIT 订单必填） */
  timeInForce?: OrderTimeInForce
  /** 是否只减仓 */
  reduceOnly?: boolean
  /** 止损/止盈价格 */
  stopPrice?: number
  /** 回调比例（0.1-10，仅追踪止损） */
  callbackRate?: number
  /** 响应格式：ACK, RESULT */
  newOrderRespType?: string
  /** 价格匹配模式 */
  priceMatch?: string
  /** 自成交防止模式 */
  selfTradePreventionMode?: string
  /** GTD 订单过期时间 */
  goodTillDate?: number
}

// ==================== 现货订单请求模型 ====================

/**
 * 现货创建订单请求
 *
 * 对应后端 SpotCreateOrderRequest
 * 严格遵循官方现货 API 文档设计
 *
 * 注意：
 * - 现货不支持：position_side, reduce_only, callback_rate, price_match, good_till_date, activation_price, working_type, price_protect, close_position
 * - 现货支持：quote_order_qty, iceberg_qty, trailing_delta, strategy_id, strategy_type
 */
export interface SpotCreateOrderRequest {
  /** 交易对符号（必填），如 BTCUSDT */
  symbol: string
  /** 订单方向：BUY 或 SELL */
  side: OrderSide
  /** 订单类型 */
  type: SpotOrderType
  /** 订单数量，必须大于0 */
  quantity?: number
  /** 客户端订单ID（可选，币安自动生成） */
  newClientOrderId?: string
  /** 限价价格（LIMIT/LIMIT_MAKER 订单必填） */
  price?: number
  /** 订单有效时间：GTC, IOC, FOK（LIMIT 订单必填） */
  timeInForce?: OrderTimeInForce
  /** 报价数量（市价买单时指定支付金额） */
  quoteOrderQty?: number
  /** 止损价格（止损单必需） */
  stopPrice?: number
  /** 冰山订单数量 */
  icebergQty?: number
  /** 追踪止损 delta */
  trailingDelta?: number
  /** 策略 ID */
  strategyId?: number
  /** 策略类型（值不能小于 1000000） */
  strategyType?: number
  /** 响应格式：ACK, RESULT, FULL */
  newOrderRespType?: string
  /** 自成交防止模式 */
  selfTradePreventionMode?: string
}

// ==================== 通用请求模型 ====================

/**
 * 创建订单请求
 *
 * 对应后端 FuturesCreateOrderRequest 或 SpotCreateOrderRequest
 * 通过 symbol 前缀区分市场类型：
 * - 现货：BINANCE:BTCUSDT
 * - 期货：BINANCE:BTCUSDT.PERP
 *
 * 注意：
 * - 前端应使用 FuturesCreateOrderRequest 或 SpotCreateOrderRequest 类型
 * - 此类型仅用于通用场景，实际推荐使用具体类型
 */
export type CreateOrderRequest = FuturesCreateOrderRequest | SpotCreateOrderRequest

/**
 * 查询订单请求
 *
 * 对应后端 GetOrderRequest
 * 至少需要提供 orderId 或 origClientOrderId 之一
 *
 * ID 优先级：orderId（币安生成的订单ID） > origClientOrderId（客户端自定义ID）
 */
export interface GetOrderRequest {
  /** 交易对符号 */
  symbol: string
  /** 币安订单ID（优先使用） */
  orderId?: number | string
  /** 客户端自定义订单ID */
  origClientOrderId?: string
}

/**
 * 查询订单列表请求
 *
 * 对应后端 ListOrdersRequest
 */
export interface ListOrdersRequest {
  /** 交易对符号 */
  symbol?: string
  /** 订单状态过滤 */
  status?: OrderStatus
  /** 起始时间（毫秒） */
  startTime?: number
  /** 结束时间（毫秒） */
  endTime?: number
  /** 返回数量限制 */
  limit?: number
}

/**
 * 撤销订单请求
 *
 * 对应后端 CancelOrderRequest
 * 至少需要提供 orderId 或 origClientOrderId 之一
 *
 * ID 优先级：orderId（币安生成的订单ID） > origClientOrderId（客户端自定义ID）
 */
export interface CancelOrderRequest {
  /** 交易对符号 */
  symbol: string
  /** 币安订单ID（优先使用） */
  orderId?: number | string
  /** 客户端自定义订单ID */
  origClientOrderId?: string
  /** 用于唯一标识此次取消操作（仅现货支持） */
  newClientOrderId?: string
  /** 取消限制条件：ONLY_NEW, ONLY_PARTIALLY_FILLED（仅现货支持） */
  cancelRestrictions?: string
}

/**
 * 查询当前挂单请求
 *
 * 对应后端 GetOpenOrdersRequest
 */
export interface GetOpenOrdersRequest {
  /** 交易对符号，不传则返回所有 */
  symbol?: string
}

// ==================== 订单修改请求模型 ====================

/**
 * 期货修改订单请求
 *
 * 对应后端 FuturesModifyOrderRequest
 * 期货 order.modify API - 可修改价格和数量，仅支持 LIMIT 订单
 *
 * ID 优先级：orderId（币安生成的订单ID） > origClientOrderId（客户端自定义ID）
 */
export interface FuturesModifyOrderRequest {
  /** 交易对符号 */
  symbol: string
  /** 订单方向：BUY 或 SELL */
  side: OrderSide
  /** 新订单数量 */
  quantity: number
  /** 新订单价格 */
  price: number
  /** 时间戳（毫秒） */
  timestamp: number
  /** 币安订单ID（优先使用） */
  orderId?: number | string
  /** 客户端自定义订单ID */
  origClientOrderId?: string
  /** 新客户端订单ID（用于标识此次修改） */
  newClientOrderId?: string
  /** 持仓方向：BOTH, LONG, SHORT */
  positionSide?: PositionSide
  /** 价格匹配模式（与 price 不能同时使用） */
  priceMatch?: string
  /** 接收窗口时间 */
  recvWindow?: number
}

/**
 * 现货修改订单请求
 *
 * 对应后端 SpotAmendOrderRequest
 * 现货 order.amend.keepPriority API - 只能减少数量
 *
 * ID 优先级：orderId（币安生成的订单ID） > origClientOrderId（客户端自定义ID）
 */
export interface SpotAmendOrderRequest {
  /** 交易对符号 */
  symbol: string
  /** 新订单数量（必须小于原订单数量） */
  newQty: number
  /** 时间戳（毫秒） */
  timestamp: number
  /** 币安订单ID（优先使用） */
  orderId?: number | string
  /** 客户端自定义订单ID */
  origClientOrderId?: string
  /** 新客户端订单ID（用于标识此次修改） */
  newClientOrderId?: string
  /** 接收窗口时间（最大60000） */
  recvWindow?: number
}

// ==================== 响应模型 ====================

/**
 * 订单数据
 *
 * 对应后端 OrderData
 * 包含订单的完整信息
 */
export interface OrderData {
  /** 客户端订单ID */
  clientOrderId?: string
  /** 币安订单ID */
  orderId?: number
  /** 交易对 */
  symbol: string
  /** 订单状态 */
  status?: OrderStatus
  /** 订单方向 */
  side?: OrderSide
  /** 订单类型 */
  type?: string
  /** 订单价格 */
  price?: string
  /** 原始数量 */
  origQty?: string
  /** 已执行数量 */
  executedQty?: string
  /** 平均成交价格 */
  avgPrice?: string
  /** 订单有效时间 */
  timeInForce?: string
  /** 持仓方向（仅期货） */
  positionSide?: PositionSide
  /** 止损价格 */
  stopPrice?: string
  /** 是否只减仓（仅期货） */
  reduceOnly?: boolean
  /** 创建时间（毫秒） */
  createTime?: number
  /** 更新时间（毫秒） */
  updateTime?: number
  /** 币安API原始数据 */
  data?: Record<string, unknown>
  /** 创建时间 */
  createdAt?: string
  /** 更新时间 */
  updatedAt?: string
}

/**
 * 订单列表数据
 *
 * 对应后端 OrderListData
 */
export interface OrderListData {
  /** 订单列表 */
  orders: OrderData[]
  /** 订单数量 */
  count: number
}

/**
 * 订单更新推送数据
 *
 * 对应后端 OrderUpdateData
 * 继承 OrderData，额外包含实时更新的时间戳
 */
export interface OrderUpdateData extends OrderData {
  /** 更新时间戳（毫秒） */
  updateTime?: number
}

/**
 * 取消订单响应数据
 *
 * 对应后端 OrderCancelResponseData
 */
export interface OrderCancelResponseData {
  taskId?: number
  status: string
  orderId?: string
  origClientOrderId?: string
}

/**
 * 期货修改订单响应数据
 *
 * 对应后端 FuturesModifyOrderResponseData
 */
export interface FuturesModifyOrderResponseData {
  taskId?: number
  status: string
  origClientOrderId?: string
  orderId?: number
  symbol?: string
  price?: string
  avgPrice?: string
  origQty?: string
  executedQty?: string
  type?: string
  side?: string
  positionSide?: string
  stopPrice?: string
  timeInForce?: string
  updateTime?: number
}

/**
 * 现货修改订单响应数据
 *
 * 对应后端 SpotAmendOrderResponseData
 */
export interface SpotAmendOrderResponseData {
  taskId?: number
  status: string
  origClientOrderId?: string
  transactTime?: number
  executionId?: number
  amendedOrderId?: number
  amendedSymbol?: string
  amendedPrice?: string
  amendedQty?: string
  amendedExecutedQty?: string
  amendedStatus?: string
  amendedOrderType?: string
  amendedSide?: string
  amendedTimeInForce?: string
}

