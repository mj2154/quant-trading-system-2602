/**
 * Trading Types - Type definitions for trading functionality
 * Based on design document: docs/frontend/design/TRADING.md
 */

// Market types
export type MarketType = 'FUTURES' | 'SPOT'

// Order direction
export type OrderSide = 'BUY' | 'SELL'

// Order types
export type OrderType =
  | 'LIMIT'
  | 'MARKET'
  | 'STOP'
  | 'STOP_LOSS'
  | 'STOP_LOSS_LIMIT'
  | 'TAKE_PROFIT'
  | 'TAKE_PROFIT_LIMIT'
  | 'LIMIT_MAKER'
  | 'TRAILING_STOP_MARKET'

// Position direction (futures only)
export type PositionSide = 'BOTH' | 'LONG' | 'SHORT'

// Time in force
export type TimeInForce = 'GTC' | 'IOC' | 'FOK' | 'GTD'

// Self trade prevention mode
export type SelfTradePreventionMode = 'EXPIRE_TAKER' | 'EXPIRE_MAKER' | 'EXPIRE_BOTH' | 'NONE'

// Price match mode (futures)
export type PriceMatch = 'OPPONENT' | 'OPPONENT_5' | 'OPPONENT_10' | 'OPPONENT_20' | 'QUEUE' | 'QUEUE_5' | 'QUEUE_10' | 'QUEUE_20' | 'NONE'

// New order response type
export type NewOrderRespType = 'ACK' | 'RESULT' | 'FULL'

// Order status
export type OrderStatus =
  | 'NEW'
  | 'PARTIALLY_FILLED'
  | 'FILLED'
  | 'CANCELED'
  | 'PENDING_CANCEL'
  | 'REJECTED'
  | 'EXPIRED'

// Create order parameters
export interface CreateOrderParams {
  marketType: MarketType
  symbol: string
  side: OrderSide
  orderType: OrderType
  quantity?: number
  quoteOrderQty?: number  // 现货市价单使用报价数量
  price?: number
  timeInForce?: TimeInForce
  stopPrice?: number
  reduceOnly?: boolean
  positionSide?: PositionSide
  // 高级参数
  newClientOrderId?: string  // 自定义客户端订单ID
  newOrderRespType?: NewOrderRespType  // 响应类型
  selfTradePreventionMode?: SelfTradePreventionMode  // 自成交预防模式
  // 现货专用
  icebergQty?: number  // 冰山订单数量
  trailingDelta?: number  // 跟踪止损 delta
  strategyId?: number  // 策略ID
  strategyType?: number  // 策略类型 (必须 >= 1000000)
  // 期货专用
  priceMatch?: PriceMatch  // 价格匹配模式
  goodTillDate?: number  // GTD订单过期时间戳 (毫秒)
}

// Order entity
export interface Order {
  clientOrderId: string
  binanceOrderId?: number
  marketType: MarketType
  symbol: string
  side: OrderSide
  orderType: OrderType
  status: OrderStatus
  data: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

// Order list response
export interface OrderListResponse {
  orders: Order[]
  count: number
}

// Order update (WebSocket push)
export interface OrderUpdate {
  clientOrderId: string
  binanceOrderId?: number
  marketType: MarketType
  symbol: string
  side: OrderSide
  orderType: OrderType
  status: OrderStatus
  data: Record<string, unknown>
  updatedAt: string
}

// Order filter options
export interface OrderFilters {
  marketType?: MarketType
  symbol?: string
  status?: OrderStatus
  side?: OrderSide
  startTime?: string
  endTime?: string
  limit?: number
}

// WebSocket message types
export type TradingMessageType =
  | 'CREATE_ORDER'
  | 'GET_ORDER'
  | 'LIST_ORDERS'
  | 'CANCEL_ORDER'
  | 'GET_OPEN_ORDERS'
  | 'ORDER_DATA'
  | 'ORDER_LIST_DATA'
  | 'ORDER_UPDATE'
  | 'ERROR'

export interface TradingMessage {
  type: TradingMessageType
  data?: unknown
  error?: string
}
