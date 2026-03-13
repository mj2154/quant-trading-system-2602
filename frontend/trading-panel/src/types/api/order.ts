/**
 * 订单数据类型 - 对应后端 order_models.py
 *
 * 使用 camelCase 与 WebSocket 协议保持一致
 * 后端使用 SnakeCaseModel 接收请求，CamelCaseModel 返回响应
 *
 * v2.0 设计变更：
 * - 移除 marketType 字段，通过 symbol 前缀区分市场类型
 *   - 现货：BINANCE:BTCUSDT
 *   - 期货：BINANCE:BTCUSDT.PERP
 * - OrderType 区分期货和现货
 */

// ==================== 枚举类型 ====================

/** 订单方向 */
export type OrderSide = 'BUY' | 'SELL'

/** 订单类型（期货） */
export type FuturesOrderType =
  | 'LIMIT'
  | 'MARKET'
  | 'STOP'
  | 'STOP_MARKET'
  | 'TAKE_PROFIT'
  | 'TAKE_PROFIT_MARKET'
  | 'TRAILING_STOP_MARKET'

/** 订单类型（现货） */
export type SpotOrderType =
  | 'LIMIT'
  | 'MARKET'
  | 'LIMIT_MAKER'
  | 'STOP_LOSS'
  | 'STOP_LOSS_LIMIT'
  | 'TAKE_PROFIT'
  | 'TAKE_PROFIT_LIMIT'

/** 订单类型（通用） */
export type OrderType = FuturesOrderType | SpotOrderType

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

// ==================== 请求模型 ====================

/**
 * 创建订单请求
 *
 * 对应后端 CreateOrderRequest
 * 前端发送 camelCase，后端自动转换为 snake_case
 *
 * 注意：通过 symbol 前缀区分市场类型
 * - 现货：BINANCE:BTCUSDT
 * - 期货：BINANCE:BTCUSDT.PERP
 */
export interface CreateOrderRequest {
  /** 交易对符号（必填），通过前缀区分市场类型 */
  symbol: string
  /** 订单方向：BUY 或 SELL */
  side: OrderSide
  /** 订单类型 */
  type: OrderType
  /** 订单数量，必须大于0 */
  quantity: number
  /** 客户端订单ID（UUID格式，必填） */
  newClientOrderId: string
  /** 限价价格 */
  price?: number
  /** 订单有效时间：GTC, IOC, FOK */
  timeInForce?: OrderTimeInForce
  /** 持仓方向：BOTH, LONG, SHORT（仅期货） */
  positionSide?: PositionSide
  /** 是否只减仓（仅期货） */
  reduceOnly?: boolean
  /** 止损价格 */
  stopPrice?: number
  /** 触发价格（追踪止损） */
  activationPrice?: number
  /** 回调比例（0.1-10） */
  callbackRate?: number
  /** 触发价格类型 */
  workingType?: string
  /** 价格保护 */
  priceProtect?: boolean
  /** 是否全平仓（仅期货） */
  closePosition?: boolean
  /** 价格匹配（仅期货） */
  priceMatch?: string
  /** 报价数量（市价买单时指定支付金额，仅现货） */
  quoteOrderQty?: number
  /** 冰山订单数量（仅现货） */
  icebergQty?: number
  /** 自成交防止模式（仅现货） */
  selfTradePreventionMode?: string
  /** 响应格式：ACK, RESULT, FULL */
  newOrderRespType?: string
}

/**
 * 查询订单请求
 *
 * 对应后端 GetOrderRequest
 * 至少需要提供 orderId 或 origClientOrderId 之一
 */
export interface GetOrderRequest {
  /** 交易对符号 */
  symbol: string
  /** 币安订单ID */
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
 */
export interface CancelOrderRequest {
  /** 交易对符号 */
  symbol: string
  /** 币安订单ID */
  orderId?: number | string
  /** 客户端自定义订单ID */
  origClientOrderId?: string
  /** 用于唯一标识此次取消操作（仅现货支持） */
  newClientOrderId?: string
  /** 取消限制条件（仅现货支持） */
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

// ==================== 响应模型 ====================

/**
 * 订单数据
 *
 * 对应后端 OrderData
 * 包含订单的完整信息
 *
 * 注意：查询/取消订单时，至少需要提供 orderId 或 origClientOrderId 之一
 */
export interface OrderData {
  /** 客户端订单ID（前端生成，必填） */
  clientOrderId: string
  /** 币安订单ID（创建成功后有值） */
  binanceOrderId?: number
  /** 市场类型通过 symbol 区分：BINANCE:BTCUSDT（现货），BINANCE:BTCUSDT.PERP（期货） */
  symbol: string
  /** 订单状态 */
  status?: OrderStatus
  /** 订单方向 */
  side?: OrderSide
  /** 订单类型 */
  type?: OrderType
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

// ==================== 前端展示类型 ====================

/**
 * 创建订单参数（前端使用）
 *
 * 注意：通过 symbol 前缀区分市场类型
 * - 现货：BINANCE:BTCUSDT
 * - 期货：BINANCE:BTCUSDT.PERP
 */
export interface CreateOrderParams {
  /** 交易对（必填），通过前缀区分市场类型 */
  symbol: string
  side: OrderSide
  orderType: OrderType
  quantity?: number
  quoteOrderQty?: number
  price?: number
  timeInForce?: OrderTimeInForce
  stopPrice?: number
  reduceOnly?: boolean
  positionSide?: PositionSide
  newClientOrderId?: string
  newOrderRespType?: string
  selfTradePreventionMode?: string
  icebergQty?: number
  trailingDelta?: number
  strategyId?: number
  strategyType?: number
  priceMatch?: string
  goodTillDate?: number
}

/**
 * 订单过滤选项
 *
 * 注意：通过 symbol 区分市场类型
 */
export interface OrderFilters {
  /** 交易对 */
  symbol?: string
  status?: OrderStatus
  side?: OrderSide
  startTime?: string
  endTime?: string
  limit?: number
}

/**
 * 订单实体（前端展示用）
 *
 * 注意：市场类型通过 symbol 区分
 */
export interface Order {
  /** 客户端订单ID（前端生成，必填） */
  clientOrderId: string
  /** 币安订单ID（创建成功后有值） */
  binanceOrderId?: number
  /** 市场类型通过 symbol 区分：BINANCE:BTCUSDT（现货），BINANCE:BTCUSDT.PERP（期货） */
  symbol: string
  side: OrderSide
  orderType: OrderType
  status: OrderStatus
  data: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

/**
 * 订单列表响应
 */
export interface OrderListResponse {
  orders: Order[]
  count: number
}

/**
 * 订单更新（WebSocket推送）
 *
 * 注意：市场类型通过 symbol 区分
 */
export interface OrderUpdate {
  clientOrderId: string
  binanceOrderId?: number
  symbol: string
  side: OrderSide
  orderType: OrderType
  status: OrderStatus
  data: Record<string, unknown>
  updatedAt: string
}
