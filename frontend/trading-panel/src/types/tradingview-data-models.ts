/**
 * TradingView 图表库数据模型定义
 *
 * 基于 TradingView Charting Library 官方接口定义
 * 用于与 FastAPI 后端进行数据格式协商
 */

// ============ 基础类型 ============

/** 时间戳类型 - 自 Unix 纪元以来的毫秒数（UTC 时区） */
export type UTCTimestamp = number;

/** 分辨率字符串类型 */
export type ResolutionString = string;

/** 时区类型（OlsonDB 格式） */
export type Timezone = string;

/** 交易品种类型 */
export type SymbolType = string;

/** 可视化图表类型 */
export type SeriesFormat = "price" | "volume";

/** 数据状态类型 */
export type DataStatus = "streaming" | "endofday" | "delayed_streaming";

/** 可视化类型集合 */
export type VisiblePlotsSet = "ohlcv" | "ohlc" | "c";

// ============ 核心数据接口 ============

/**
 * K线数据接口
 * TradingView 图表库使用的标准数据格式
 */
export interface Bar {
  /** K线时间 - 自 Unix 纪元以来的毫秒数（UTC 时区） */
  time: UTCTimestamp;
  /** 开盘价 */
  open: number;
  /** 最高价 */
  high: number;
  /** 最低价 */
  low: number;
  /** 收盘价 */
  close: number;
  /** 交易量（可选） */
  volume?: number;
}

/**
 * 交易品种信息接口
 * 直接对应 TradingView LibrarySymbolInfo
 */
export interface LibrarySymbolInfo {
  /** 交易品种名称（如：AAPL、9988） */
  name: string;
  /** 基础交易品种数组（用于组合品种） */
  base_name?: string[];
  /** 唯一标识符（用于数据请求） */
  ticker?: string;
  /** 交易品种描述 */
  description: string;
  /** 详细描述（可选） */
  long_description?: string;
  /** 交易品种类型 */
  type: SymbolType;
  /** 交易时段（如：1700-0200） */
  session: string;
  /** 用于显示的交易时段（可选） */
  session_display?: string;
  /** 非交易日假期列表（YYYYMMDD格式） */
  session_holidays?: string;
  /** 交易时段修正 */
  corrections?: string;
  /** 交易所名称 */
  exchange: string;
  /** 交易所简称 */
  listed_exchange: string;
  /** 时区（OlsonDB 格式） */
  timezone: Timezone;
  /** 显示格式 */
  format: SeriesFormat;
  /** 价格精度（10^n） */
  pricescale: number;
  /** 最小变动单位 */
  minmov: number;
  /** 是否为分数定价 */
  fractional?: boolean;
  /** 分数的分数（可选） */
  minmove2?: number;
  /** 动态最小价格变动 */
  variable_tick_size?: string;
  /** 是否包含日内数据 */
  has_intraday?: boolean;
  /** 支持的分辨率列表 */
  supported_resolutions?: ResolutionString[];
  /** 日内数据倍数 */
  intraday_multipliers?: string[];
  /** 是否包含秒级数据 */
  has_seconds?: boolean;
  /** 是否包含逐笔数据 */
  has_ticks?: boolean;
  /** 秒级数据倍数 */
  seconds_multipliers?: string[];
  /** 从逐笔数据构建秒级数据 */
  build_seconds_from_ticks?: boolean;
  /** 是否包含日数据 */
  has_daily?: boolean;
  /** 日数据倍数 */
  daily_multipliers?: string[];
  /** 是否包含周和月数据 */
  has_weekly_and_monthly?: boolean;
  /** 周数据倍数 */
  weekly_multipliers?: string[];
  /** 月数据倍数 */
  monthly_multipliers?: string[];
  /** 是否包含空数据棒 */
  has_empty_bars?: boolean;
  /** 可视化图表类型 */
  visible_plots_set?: VisiblePlotsSet;
  /** 交易量精度 */
  volume_precision?: number;
  /** 数据状态 */
  data_status?: DataStatus;
  /** 延迟时间（秒） */
  delay?: number;
  /** 是否为过期合约 */
  expired?: boolean;
  /** 过期日期时间戳 */
  expiration_date?: UTCTimestamp;
  /** 行业板块 */
  sector?: string;
  /** 所属行业 */
  industry?: string;
  /** 交易货币 */
  currency_code?: string;
  /** 原始货币 */
  original_currency_code?: string;
  /** 单位ID */
  unit_id?: string;
  /** 原始单位ID */
  original_unit_id?: string;
  /** 单位转换类型 */
  unit_conversion_types?: string[];
  /** 子会话ID */
  subsession_id?: string;
  /** 子会话信息 */
  subsessions?: LibrarySubsessionInfo[];
  /** 价格来源ID */
  price_source_id?: string;
  /** 价格来源列表 */
  price_sources?: SymbolInfoPriceSource[];
  /** 交易品种Logo URL */
  logo_urls?: [string] | [string, string];
}

/**
 * 子会话信息接口
 */
export interface LibrarySubsessionInfo {
  /** 描述 */
  description: string;
  /** 子会话ID */
  id: string;
  /** 交易时段 */
  session: string;
  /** 交易时段修正 */
  "session-correction"?: string;
  /** 显示的交易时段 */
  "session-display"?: string;
}

/**
 * 价格来源接口
 */
export interface SymbolInfoPriceSource {
  /** ID */
  id: string;
  /** 名称 */
  name: string;
}

/**
 * 历史数据请求参数接口
 * 直接对应 TradingView PeriodParams
 */
export interface PeriodParams {
  /** 从指定时间戳开始（毫秒） */
  from: UTCTimestamp;
  /** 到指定时间戳结束（毫秒） */
  to: UTCTimestamp;
  /** 第一根K线的时间戳 */
  firstDataRequest?: boolean;
  /** 请求的数据加载数量 */
  countBack?: number;
}

/**
 * K线数据历史记录响应
 */
export interface HistoryResponse {
  /** K线数据数组 */
  bars: Bar[];
  /** 是否无数据 */
  noData: boolean;
}

/**
 * 搜索交易品种结果接口
 */
export interface SearchSymbolResult {
  /** 交易品种名称 */
  symbol: string;
  /** 交易品种显示名称 */
  display_name: string;
  /** 交易所名称 */
  exchange: string;
  /** 交易品种类型 */
  type: SymbolType;
  /** 描述 */
  description: string;
  /** 交易时段 */
  session: string;
  /** 时区 */
  timezone: Timezone;
  /** 交易品种ID */
  ticker_id?: string;
}

// ============ 报价数据接口（Watchlist用）===========

/**
 * 报价数据接口
 * 直接对应 TradingView DatafeedQuoteValues
 */
export interface DatafeedQuoteValues {
  /** 价格变动（绝对值） */
  ch?: number;
  /** 价格变动百分比 */
  chp?: number;
  /** 交易品种短名称 */
  short_name?: string;
  /** 交易所名称 */
  exchange?: string;
  /** 交易品种描述 */
  description?: string;
  /** 最新成交价（最后价格） */
  lp?: number;
  /** 卖一价（Ask price） */
  ask?: number;
  /** 买一价（Bid price） */
  bid?: number;
  /** 买卖价差 */
  spread?: number;
  /** 今日开盘价 */
  open_price?: number;
  /** 今日最高价 */
  high_price?: number;
  /** 今日最低价 */
  low_price?: number;
  /** 昨收价（前一交易日收盘价） */
  prev_close_price?: number;
  /** 今日成交量 */
  volume?: number;
  /** 原始交易品种名称 */
  original_name?: string;
  /** 盘前/盘后价格 */
  rtc?: number;
  /** 盘前/盘后价格更新时间 */
  rtc_time?: number;
  /** 盘前/盘后价格变动 */
  rch?: number;
  /** 盘前/盘后价格变动百分比 */
  rchp?: number;
  /** 自定义字段支持 */
  [valueName: string]: string | number | string[] | number[] | undefined;
}

/**
 * Quote 数据响应接口
 * 直接对应 TradingView QuoteDataResponse
 */
export interface QuoteDataResponse {
  /** 状态码：ok | error */
  s: "ok" | "error";
  /** 交易品种名称（必须与请求中的名称完全相同） */
  n: string;
  /** 报价值 */
  v: unknown;
}

/**
 * Quote 数据错误响应
 */
export interface QuoteErrorData extends QuoteDataResponse {
  /** @inheritDoc */
  s: "error";
  /** @inheritDoc */
  v: object;
}

/**
 * Quote 数据成功响应
 */
export interface QuoteOkData extends QuoteDataResponse {
  /** @inheritDoc */
  s: "ok";
  /** @inheritDoc */
  v: DatafeedQuoteValues;
}

/**
 * 联合类型：所有 Quote 数据
 * 直接对应 TradingView QuoteData
 */
export type QuoteData = QuoteOkData | QuoteErrorData;

// ============ 数据源 API 接口 ============

/**
 * Quote 数据回调函数类型
 * 直接对应 TradingView QuotesCallback
 */
export type QuotesCallback = (data: QuoteData[]) => void;

/**
 * Quote 错误回调函数类型
 * 直接对应 TradingView QuotesErrorCallback
 */
export type QuotesErrorCallback = (reason: string) => void;

/**
 * 数据源报价 API 接口
 * 直接对应 TradingView IDatafeedQuotesApi
 */
export interface IDatafeedQuotesApi {
  /** 获取报价数据 */
  getQuotes(
    symbols: string[],
    onDataCallback: QuotesCallback,
    onErrorCallback: QuotesErrorCallback
  ): void;

  /**
   * 订阅实时报价更新
   * @param symbols 观察列表中不可见的标的
   * @param fastSymbols 当前可见或活跃的标的
   * @param onRealtimeCallback 实时数据回调（收到数据时立即调用）
   * @param listenerGUID 监听器唯一标识
   */
  subscribeQuotes(
    symbols: string[],
    fastSymbols: string[],
    onRealtimeCallback: QuotesCallback,
    listenerGUID: string
  ): void;

  /** 取消订阅实时报价 */
  unsubscribeQuotes(listenerGUID: string): void;
}

/**
 * 数据源配置接口
 * 直接对应 TradingView DatafeedConfiguration
 */
export interface DatafeedConfiguration {
  /** 支持的分辨率列表 */
  supported_resolutions: ResolutionString[];
  /** 是否支持搜索 */
  supports_search?: boolean;
  /** 是否支持组请求 */
  supports_group_request?: boolean;
}

/**
 * 外部数据源接口
 * 直接对应 TradingView IExternalDatafeed
 */
export interface IExternalDatafeed {
  /** 数据源就绪 */
  onReady(callback: (config: DatafeedConfiguration) => void): void;
}

/**
 * 数据源图表 API 接口
 * 直接对应 TradingView IDatafeedChartApi
 */
export interface IDatafeedChartApi {
  /** 搜索交易品种 */
  searchSymbols(
    userInput: string,
    exchange: string,
    symbolType: string,
    onResultReadyCallback: (symbols: SearchSymbolResult[]) => void
  ): void;

  /** 解析交易品种 */
  resolveSymbol(
    symbolName: string,
    onSymbolResolvedCallback: (symbol: LibrarySymbolInfo) => void,
    onResolveErrorCallback: (error: string) => void,
    extension?: any
  ): void;

  /** 获取K线数据 */
  getBars(
    symbolInfo: LibrarySymbolInfo,
    resolution: ResolutionString,
    periodParams: PeriodParams,
    onHistoryCallback: (bars: Bar[], meta: HistoryResponse) => void,
    onErrorCallback: (error: string) => void
  ): void;

  /** 订阅K线数据更新 */
  subscribeBars(
    symbolInfo: LibrarySymbolInfo,
    resolution: ResolutionString,
    onRealtimeCallback: (bar: Bar) => void,
    subscriberUID: string,
    onResetCacheNeededCallback: () => void
  ): void;

  /** 取消订阅K线数据 */
  unsubscribeBars(subscriberUID: string): void;
}

/**
 * 基础数据源接口
 * 直接对应 TradingView IBasicDataFeed
 */
export type IBasicDataFeed = IDatafeedChartApi & IExternalDatafeed;

// ============ 深度行情接口 ============

/**
 * 深度行情级别接口
 */
export interface DOMLevel {
  /** 价格 */
  price: number;
  /** 数量 */
  volume: number;
}

/**
 * 市场深度数据接口
 */
export interface MarketDepth {
  /** 是否为快照数据 */
  snapshot: boolean;
  /** 卖单级别（按价格升序排列） */
  asks: DOMLevel[];
  /** 买单级别（按价格升序排列） */
  bids: DOMLevel[];
}

// ============ FastAPI 后端接口定义 ============

/**
 * 后端 API 响应格式
 */
export interface ApiResponse<T = any> {
  /** 响应码 */
  code: number;
  /** 响应消息 */
  message: string;
  /** 数据 */
  data: T;
  /** 时间戳 */
  timestamp: UTCTimestamp;
}

/**
 * K线数据 API 响应
 */
export interface BarApiResponse extends ApiResponse<{
  /** K线数据数组 */
  bars: Bar[];
  /** 总数量 */
  total: number;
  /** 是否还有更多数据 */
  hasMore: boolean;
}> {}

/**
 * 交易品种信息 API 响应
 */
export interface SymbolApiResponse extends ApiResponse<{
  /** 交易品种列表 */
  symbols: LibrarySymbolInfo[];
}> {}

/**
 * 报价数据 API 响应
 */
export interface QuoteApiResponse extends ApiResponse<{
  /** 报价数据数组 */
  quotes: QuoteData[];
  /** 更新时间 */
  updatedAt: UTCTimestamp;
}> {}

/**
 * 数据源配置 API 响应
 */
export interface DatafeedConfigApiResponse extends ApiResponse<DatafeedConfiguration> {}

/**
 * 搜索结果 API 响应
 */
export interface SearchApiResponse extends ApiResponse<{
  /** 搜索结果数组 */
  results: SearchSymbolResult[];
}> {}

// ============ WebSocket 消息接口 ============

/**
 * WebSocket 消息类型定义
 */
export interface WebSocketMessage {
  /** 消息类型 */
  type: 'subscribe' | 'unsubscribe' | 'bar' | 'quote' | 'error';
  /** 交易品种 */
  symbol?: string;
  /** 分辨率 */
  resolution?: ResolutionString;
  /** 数据 */
  data?: any;
  /** 时间戳 */
  timestamp: UTCTimestamp;
}

/**
 * K线数据 WebSocket 消息
 */
export interface BarWebSocketMessage extends WebSocketMessage {
  type: 'bar';
  data: Bar;
}

/**
 * 报价数据 WebSocket 消息
 */
export interface QuoteWebSocketMessage extends WebSocketMessage {
  type: 'quote';
  data: QuoteData[];
}

// ============ 工具函数 ============

/**
 * 数据验证工具函数
 */
export class DataValidators {
  /** 验证时间戳格式 */
  static isValidUTCTimestamp(timestamp: any): timestamp is UTCTimestamp {
    return typeof timestamp === 'number' && timestamp > 0 && timestamp < Date.now() + 365 * 24 * 60 * 60 * 1000;
  }

  /** 验证价格格式 */
  static isValidPrice(price: any): price is number {
    return typeof price === 'number' && !isNaN(price) && price >= 0;
  }

  /** 验证交易量格式 */
  static isValidVolume(volume: any): volume is number {
    return typeof volume === 'number' && !isNaN(volume) && volume >= 0;
  }

  /** 验证K线数据格式 */
  static isValidBar(bar: any): bar is Bar {
    return (
      bar &&
      typeof bar === 'object' &&
      this.isValidUTCTimestamp(bar.time) &&
      this.isValidPrice(bar.open) &&
      this.isValidPrice(bar.high) &&
      this.isValidPrice(bar.low) &&
      this.isValidPrice(bar.close) &&
      (bar.volume === undefined || this.isValidVolume(bar.volume))
    );
  }

  /** 验证交易品种信息格式 */
  static isValidSymbolInfo(symbolInfo: any): symbolInfo is LibrarySymbolInfo {
    return (
      symbolInfo &&
      typeof symbolInfo === 'object' &&
      typeof symbolInfo.name === 'string' &&
      typeof symbolInfo.description === 'string' &&
      typeof symbolInfo.type === 'string' &&
      typeof symbolInfo.timezone === 'string' &&
      typeof symbolInfo.pricescale === 'number' &&
      typeof symbolInfo.minmov === 'number'
    );
  }
}

/**
 * 数据转换工具函数
 */
export class DataTransformers {
  /** 将第三方K线数据转换为Bar格式 */
  static toBar(thirdPartyData: any): Bar {
    return {
      time: new Date(thirdPartyData.timestamp).getTime(),
      open: Number(thirdPartyData.open),
      high: Number(thirdPartyData.high),
      low: Number(thirdPartyData.low),
      close: Number(thirdPartyData.close),
      volume: thirdPartyData.volume ? Number(thirdPartyData.volume) : undefined
    };
  }

  /** 将Bar数据转换为第三方数据格式 */
  static fromBar(bar: Bar): any {
    return {
      timestamp: new Date(bar.time).toISOString(),
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
      volume: bar.volume
    };
  }

  /** 格式化价格显示 */
  static formatPrice(price: number, pricescale: number): string {
    const decimals = Math.log10(pricescale);
    return price.toFixed(decimals);
  }

  /** 格式化交易量显示 */
  static formatVolume(volume: number, precision: number = 0): string {
    if (volume >= 1e9) {
      return (volume / 1e9).toFixed(precision) + 'B';
    } else if (volume >= 1e6) {
      return (volume / 1e6).toFixed(precision) + 'M';
    } else if (volume >= 1e3) {
      return (volume / 1e3).toFixed(precision) + 'K';
    }
    return volume.toFixed(precision);
  }
}

// ============ 常量定义 ============

/**
 * TradingView 常量
 */
export const TRADINGVIEW_CONSTANTS = {
  /** 默认交易量精度 */
  DEFAULT_VOLUME_PRECISION: 0,
  /** 默认价格精度 */
  DEFAULT_PRICESCALE: 100,
  /** 默认最小变动单位 */
  DEFAULT_MINMOV: 1,
  /** 最大历史数据请求数量 */
  MAX_HISTORY_BARS: 20000,
  /** WebSocket 重连间隔（毫秒） */
  WS_RECONNECT_INTERVAL: 2000,
  /** API 请求超时时间（毫秒） */
  API_TIMEOUT: 30000
} as const;

/**
 * 常用的分辨率配置
 */
export const COMMON_RESOLUTIONS = {
  /** 加密货币 */
  CRYPTO: ['1', '5', '15', '60', '240', '1D', '1W', '1M'],
  /** 股票 */
  STOCK: ['1', '5', '15', '60', '1D', '1W', '1M'],
  /** 外汇 */
  FOREX: ['1', '5', '15', '60', '240', '1D', '1W', '1M'],
  /** 期货 */
  FUTURES: ['1', '5', '15', '60', '1D', '1W', '1M']
} as const;

/**
 * 交易品种类型常量
 */
export const SYMBOL_TYPES = {
  /** 股票 */
  STOCK: 'stock',
  /** 加密货币 */
  CRYPTO: 'crypto',
  /** 外汇 */
  FOREX: 'forex',
  /** 期货 */
  FUTURES: 'futures',
  /** 指数 */
  INDEX: 'index',
  /** 商品 */
  COMMODITY: 'commodity',
  /** 债券 */
  BOND: 'bond'
} as const;