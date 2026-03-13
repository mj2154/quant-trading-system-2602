/**
 * 报价数据类型 - 对应后端 quote_models.py
 *
 * 使用 camelCase 与 WebSocket 协议保持一致
 * 后端使用 CamelCaseModel 序列化，自动转为 camelCase
 */

// ==================== 报价数据 ====================

/**
 * 统一报价值模型
 *
 * 期货和现货共用的报价数据格式。
 * 对应后端 QuotesValue
 */
export interface QuotesValue {
  /** 价格变化 */
  ch: number
  /** 价格变化百分比 */
  chp: number
  /** 短名称（如 BTCUSDT） */
  shortName: string
  /** 交易所名称（如 BINANCE） */
  exchange: string
  /** 标的描述（如 比特币/泰达币） */
  description: string
  /** 最新价格（last price） */
  lp: number
  /** 卖价 */
  ask: number
  /** 买价 */
  bid: number
  /** 价差 */
  spread: number
  /** 开盘价 */
  openPrice: number
  /** 最高价 */
  highPrice: number
  /** 最低价 */
  lowPrice: number
  /** 前收盘价 */
  prevClosePrice?: number
  /** 成交量 */
  volume: number
}

/**
 * 报价数据
 *
 * 符合TradingView quotes API格式。
 * 对应后端 QuotesData
 */
export interface QuotesData {
  /** 标的全名（EXCHANGE:SYMBOL格式） */
  n: string
  /** 状态（ok/error） */
  s: string
  /** 报价值对象 */
  v: QuotesValue
}

/**
 * 报价数据列表
 *
 * 包含多个交易对的报价数据。
 * 对应后端 QuotesList
 */
export interface QuotesList {
  /** 报价数据列表 */
  quotes: QuotesData[]
}

// ==================== 订单簿数据 ====================

/**
 * 价格层级
 *
 * 用于订单簿深度数据。
 * 对应后端 PriceLevel
 */
export interface PriceLevel {
  /** 价格 */
  price: number
  /** 数量 */
  quantity: number
}

/**
 * 订单簿数据
 *
 * 包含买卖盘深度信息。
 * 对应后端 OrderBookData
 */
export interface OrderBookData {
  /** 交易对 */
  symbol: string
  /** 买盘（从高到低） */
  bids: PriceLevel[]
  /** 卖盘（从低到高） */
  asks: PriceLevel[]
  /** 最后更新ID */
  lastUpdateId: number
}

// ==================== 请求参数 ====================

/**
 * 获取报价请求参数
 */
export interface GetQuotesParams {
  /** 交易对列表 */
  symbols: string[]
}

/**
 * 获取订单簿请求参数
 */
export interface GetOrderBookParams {
  /** 交易对 */
  symbol: string
  /** 深度限制 */
  limit?: number
}
