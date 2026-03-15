/**
 * API 类型统一导出
 *
 * 对应后端 services/api-service/src/models/ 目录下的所有 Pydantic 模型
 * 使用 camelCase 与 WebSocket 协议保持一致
 *
 * 目录结构：
 * - kline.ts    - K线数据模型，对应 kline_models.py
 * - quote.ts    - 报价数据模型，对应 quote_models.py
 * - order.ts    - 订单数据模型，对应 order_models.py
 * - account.ts  - 账户数据模型，对应 account_models.py
 * - signal.ts   - 信号数据模型，对应 signal_models.py
 * - alert.ts    - 告警数据模型，对应 alert_config_models.py
 * - config.ts   - 配置/搜索/订阅/指标数据模型，对应 ws_payload.py
 */

// ==================== 配置与搜索类型 ====================

export type {
  SymbolType,
  ConfigData,
  SymbolSearchItem,
  SearchSymbolsData,
  SubscriptionItem,
  FailedSubscription,
  SubscriptionsData,
  SubscribeData,
  SystemMetrics,
  MetricsData,
  ServerTimeData,
} from './config'

// ==================== K线类型 ====================

export type {
  KlineBar,
  KlineData,
  KlineBars,
  KlineMeta,
  KlineResponse,
  GetKlinesParams,
} from './kline'

// ==================== 报价类型 ====================

export type {
  QuotesValue,
  QuotesData,
  QuotesList,
  PriceLevel,
  OrderBookData,
  GetQuotesParams,
  GetOrderBookParams,
} from './quote'

// ==================== 订单类型 ====================

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
  CreateOrderParams,
  OrderFilters,
  Order,
  OrderListResponse,
  OrderUpdate,
} from './order'

// ==================== 账户类型 ====================

export type {
  SpotBalance,
  SpotCommissionRates,
  SpotAccountInfo,
  FuturesAsset,
  FuturesPosition,
  FuturesAccountInfo,
  AccountInfo,
  AccountResponse,
  AccountBalance,
  PositionInfo,
  AccountOverview,
  PositionItem,
  BalanceItem,
} from './account'

// ==================== 信号类型 ====================

export type {
  StrategyParam,
  StrategyMetadata,
  StrategyMetadataListResponse,
  SignalRecord,
  SignalListResponse,
  SignalRecordQueryParams,
  EnableDisableResponse as EnableDisableSignalResponse,
} from './signal'

// ==================== 告警类型 ====================

export type {
  AlertTriggerType,
  AlertStrategyType,
  CreateAlertSignalRequest,
  UpdateAlertSignalRequest,
  DeleteAlertSignalRequest,
  EnableAlertSignalRequest,
  ListAlertSignalsRequest,
  AlertSignalResponse,
  AlertSignalListResponse,
  EnableDisableAlertResponse,
  AlertConfig,
  AlertConfigListResponse,
  AlertMacdParams,
  AlertParams,
  ALERT_TRIGGER_TYPE_OPTIONS,
  ALERT_STRATEGY_TYPE_OPTIONS,
  INTERVAL_OPTIONS,
  SYMBOL_OPTIONS,
} from './alert'

// ==================== 订阅类型 ====================

import type { KlineBar } from './kline'
import type { SignalRecord } from './signal'
import type { Order } from './order'
import type { QuotesValue } from './quote'

/**
 * 订阅选项配置
 */
export interface SubscriptionOptions {
  /** 断开重连后是否自动恢复订阅 */
  reconnect?: boolean
  /** 订阅优先级 (数值越小优先级越高) */
  priority?: number
  /** 订阅标签，用于追踪 */
  label?: string
}

/**
 * 订阅回调函数类型
 */
export type SubscriptionCallback<T> = (data: T, subscriptionKey?: string) => void

/**
 * 交易数据
 */
export interface TradeData {
  symbol: string
  price: number
  quantity: number
  time: number
  isBuyerMaker: boolean
  tradeId: string
}

/**
 * 账户增量更新数据
 */
export interface AccountUpdate {
  accountType: 'SPOT' | 'FUTURES'
  balances: Array<{
    asset: string
    free: number
    locked: number
  }>
  timestamp: number
}

/**
 * 订阅数据类型联合
 */
export type SubscriptionData =
  | { type: 'kline'; data: KlineBar; subscriptionKey: string }
  | { type: 'quotes'; data: QuotesValue; subscriptionKey: string }
  | { type: 'trade'; data: TradeData; subscriptionKey: string }
  | { type: 'account'; data: AccountUpdate; subscriptionKey: string }
  | { type: 'signal'; data: SignalRecord; subscriptionKey: string }
  | { type: 'order'; data: Order; subscriptionKey: string }

/**
 * 存储的订阅信息
 */
export interface SubscriptionInfo<T = unknown> {
  /** 订阅键 */
  key: string
  /** 回调函数 */
  callback: SubscriptionCallback<T>
  /** 订阅选项 */
  options: SubscriptionOptions
  /** 订阅时间戳 */
  subscribedAt: number
  /** 订阅状态 */
  status: 'active' | 'inactive' | 'error'
  /** 错误信息 */
  error?: string
}

/**
 * K线订阅选项
 */
export interface KlineSubscriptionOptions extends SubscriptionOptions {
  /** K线周期 (如 '1', '5', '60', '1D') */
  interval: string
}

/**
 * 报价订阅选项
 */
export interface QuotesSubscriptionOptions extends SubscriptionOptions {
  /** 交易对列表 */
  symbols: string[]
}

/**
 * 账户订阅选项
 */
export interface AccountSubscriptionOptions extends SubscriptionOptions {
  /** 账户类型 */
  accountType: 'SPOT' | 'FUTURES'
}

/**
 * 信号订阅选项
 */
export interface SignalSubscriptionOptions extends SubscriptionOptions {
  /** 告警ID */
  alertId: string
}
