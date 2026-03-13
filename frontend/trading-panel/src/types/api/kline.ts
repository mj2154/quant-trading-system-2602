/**
 * K线数据类型 - 对应后端 kline_models.py
 *
 * 使用 camelCase 与 WebSocket 协议保持一致
 * 后端使用 CamelCaseModel 序列化，自动转为 camelCase
 */

// ==================== K线数据 ====================

/**
 * K线Bar数据
 *
 * 包含OHLCV（开高低收成交量）数据。
 * 对应后端 KlineBar
 */
export interface KlineBar {
  /** Bar时间戳（毫秒） */
  time: number
  /** 开盘价 */
  open: number
  /** 最高价 */
  high: number
  /** 最低价 */
  low: number
  /** 收盘价 */
  close: number
  /** 成交量 */
  volume: number
}

/**
 * 单个K线数据
 *
 * 包含Bar数据和元信息。
 * 对应后端 KlineData
 */
export interface KlineData {
  /** 交易对，如 "BINANCE:BTCUSDT" */
  symbol: string
  /** K线周期，如 "1", "5", "60", "1D" */
  interval: string
  /** Bar数据 */
  bar: KlineBar
  /** Bar是否已关闭 */
  isBarClosed: boolean
}

/**
 * K线数据列表
 *
 * 包含多个K线Bar和元信息。
 * 对应后端 KlineBars
 */
export interface KlineBars {
  /** 交易对 */
  symbol: string
  /** K线周期 */
  interval: string
  /** Bar列表 */
  bars: KlineBar[]
  /** Bar数量 */
  count: number
  /** 是否无数据 */
  noData: boolean
  /** 下一页时间 */
  nextTime?: number
}

/**
 * K线元数据
 *
 * 包含K线请求的元信息。
 * 对应后端 KlineMeta
 */
export interface KlineMeta {
  /** 交易对 */
  symbol: string
  /** K线周期 */
  interval: string
  /** 开始时间 */
  fromTime?: number
  /** 结束时间 */
  to?: number
  /** Bar数量 */
  count: number
  /** 是否无数据 */
  noData: boolean
  /** 下一页时间 */
  nextTime?: number
}

/**
 * K线响应数据
 *
 * 包含K线数据和元信息。
 * 对应后端 KlineResponse
 */
export interface KlineResponse {
  /** K线数据列表 */
  data: KlineBar[]
  /** 元信息 */
  meta: KlineMeta
}

// ==================== 请求参数 ====================

/**
 * 获取K线请求参数
 */
export interface GetKlinesParams {
  /** 交易对 */
  symbol: string
  /** K线周期 */
  interval: string
  /** 开始时间（毫秒） */
  fromTime?: number
  /** 结束时间（毫秒） */
  toTime?: number
  /** 数量限制 */
  limit?: number
}
