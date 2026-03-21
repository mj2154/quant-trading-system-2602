/**
 * 类型定义统一导出
 *
 * 本项目采用分层类型设计：
 * 1. api/ - 对应后端 API 数据模型（推荐使用）
 * 2. 旧版类型文件 - 向后兼容，未来将逐步迁移到 api/
 *
 * 推荐使用方式：
 * import { KlineBar, Order, SpotAccountInfo } from '@/types/api'
 */

// ==================== API 类型（推荐） ====================

// K线类型
export type {
  KlineBar,
  KlineData,
  KlineBars,
  KlineMeta,
  KlineResponse,
  GetKlinesParams,
} from './api/kline'

// 报价类型
export type {
  QuotesData,
  QuotesList,
  PriceLevel,
  OrderBookData,
  GetQuotesParams,
  GetOrderBookParams,
} from './api/quote'

// 订单类型
export type {
  OrderSide,
  OrderType,
  FuturesOrderType,
  SpotOrderType,
  OrderTimeInForce,
  OrderStatus,
  PositionSide,
  CreateOrderRequest,
  GetOrderRequest,
  ListOrdersRequest,
  CancelOrderRequest,
  GetOpenOrdersRequest,
  OrderData,
  OrderListData,
  OrderUpdateData,
} from './api/order'

// 账户类型
export type {
  SpotBalance,
  SpotCommissionRates,
  SpotAccountDetail,
  SpotAccountData,
  FuturesAccountAsset,
  FuturesAccountPosition,
  FuturesAccountDetail,
  FuturesAccountData,
} from './api/account'

// 信号类型
export type {
  StrategyParam,
  StrategyMetadata,
  StrategyMetadataListResponse,
  SignalRecord,
  SignalListResponse,
  SignalRecordQueryParams,
  EnableDisableResponse as EnableDisableSignalResponse,
} from './api/signal'

// 告警类型
export type {
  AlertTriggerType,
  AlertStrategyType,
  CreateAlertConfigRequest,
  UpdateAlertConfigRequest,
  DeleteAlertConfigRequest,
  ListAlertConfigsRequest,
  AlertConfigResponse,
  AlertConfigListResponse,
  AlertConfig,
  ALERT_TRIGGER_TYPE_OPTIONS,
  ALERT_STRATEGY_TYPE_OPTIONS,
  INTERVAL_OPTIONS,
  SYMBOL_OPTIONS,
} from './api/alert'

// 订阅类型
export type {
  SubscriptionOptions,
  SubscriptionCallback,
  SubscriptionData,
  SubscriptionInfo,
  QuotesValue,
  TradeData,
  AccountUpdate,
  KlineSubscriptionOptions,
  QuotesSubscriptionOptions,
  AccountSubscriptionOptions,
  SignalSubscriptionOptions,
} from './api/index'

// ==================== WebSocket 消息类型 ====================
// 这些类型尚未在 api/ 中定义，保留在 trading-types.ts 中

export type {
  TradingMessageType,
  TradingMessage,
} from './trading-types'
