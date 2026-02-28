/**
 * 告警信号类型定义
 *
 * 对应后端 Strategy/AlertSignal Pydantic 模型
 * 使用 camelCase 与 WebSocket 协议保持一致
 */

// ==================== 联合类型定义 ====================

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
  | 'each_minute';

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
  | 'Alpha01Strategy';

/**
 * MACD 参数配置
 */
export interface AlertMacdParams {
  fast1: number;
  slow1: number;
  signal1: number;
  fast2: number;
  slow2: number;
  signal2: number;
}

/**
 * 告警参数配置
 * 根据不同策略类型有不同的参数结构
 */
export interface AlertParams {
  /** MACD快速周期 */
  fastPeriod?: number;
  /** MACD慢速周期 */
  slowPeriod?: number;
  /** MACD信号线周期 */
  signalPeriod?: number;
  /** 阈值设置 */
  threshold?: number;
  /** 策略特定参数 */
  [key: string]: unknown;
}

// ==================== 主类型定义 ====================

/**
 * 告警信号配置
 * 对应后端 StrategyConfig 模型（适配告警术语）
 * 使用 camelCase 与 WebSocket 协议保持一致
 */
export interface AlertSignal {
  /** 告警ID */
  id: string;
  /** 告警名称 */
  name: string;
  /** 告警描述 */
  description: string | null;
  /** 策略类型 */
  strategyType: AlertStrategyType;
  /** 交易品种 */
  symbol: string;
  /** K线周期 */
  interval: string;
  /** 触发类型 */
  triggerType: AlertTriggerType;
  /** 策略参数 */
  params: Record<string, number | boolean> | null;
  /** 是否启用 */
  isEnabled: boolean;
  /** 创建人 */
  createdBy: string | null;
  /** 创建时间 */
  createdAt: string;
  /** 更新时间 */
  updatedAt: string;
}

/**
 * 创建告警信号请求
 */
export interface CreateAlertSignalRequest {
  /** 告警名称 */
  name: string;
  /** 告警描述（可选） */
  description?: string;
  /** 策略类型 */
  strategyType: AlertStrategyType;
  /** 交易品种 */
  symbol: string;
  /** K线周期 */
  interval: string;
  /** 触发类型 */
  triggerType: AlertTriggerType;
  /** 策略参数 */
  params?: Record<string, number | boolean>;
  /** 是否启用（默认true） */
  isEnabled?: boolean;
}

/**
 * 更新告警信号请求
 * 所有字段可选，用于部分更新
 */
export interface UpdateAlertSignalRequest {
  /** 告警名称 */
  name?: string;
  /** 告警描述 */
  description?: string;
  /** 策略类型 */
  strategyType?: AlertStrategyType;
  /** 交易品种 */
  symbol?: string;
  /** K线周期 */
  interval?: string;
  /** 触发类型 */
  triggerType?: AlertTriggerType;
  /** 策略参数 */
  params?: Record<string, number | boolean>;
  /** 是否启用 */
  isEnabled?: boolean;
}

// ==================== 信号记录类型 ====================

/**
 * 信号记录
 * 告警触发后产生的信号记录
 * 使用 camelCase 与 WebSocket 协议保持一致
 */
export interface SignalRecord {
  /** 信号ID（数据库自增ID） */
  id: number;
  /** 关联的告警ID (UUID) */
  alertId: string;
  /** 关联的配置ID */
  configId: string | null;
  /** 策略名称 */
  strategyName: string;
  /** 交易品种 */
  symbol: string;
  /** K线周期 */
  interval: string;
  /** 触发类型 */
  triggerType: string | null;
  /** 信号值 */
  signalValue: boolean | null;
  /** 信号原因 */
  signalReason: string | null;
  /** 计算时间 */
  computedAt: string;
  /** 数据订阅键 */
  sourceSubscriptionKey: string | null;
  /** 附加元数据 */
  metadata: Record<string, unknown>;
}

/**
 * 信号记录列表响应
 */
export interface SignalRecordListResponse {
  /** 信号记录数组 */
  items: SignalRecord[];
  /** 总数 */
  total: number;
  /** 当前页码 */
  page: number;
  /** 每页数量 */
  pageSize: number;
}

/**
 * 信号记录查询参数
 * 与设计文档 list_signals 参数保持一致
 * 使用 camelCase 与 WebSocket 协议保持一致
 */
export interface SignalRecordQueryParams {
  /** 页码 */
  page?: number;
  /** 每页数量 */
  pageSize?: number;
  /** 交易品种筛选 */
  symbol?: string;
  /** 策略类型筛选 */
  strategyType?: string;
  /** K线周期筛选 */
  interval?: number;
  /** 信号值筛选 */
  signalValue?: boolean;
  /** 创建者筛选 */
  createdBy?: string;
  /** 起始时间戳（毫秒） */
  fromTime?: number;
  /** 结束时间戳（毫秒） */
  toTime?: number;
  /** 排序字段 */
  orderBy?: string;
  /** 排序方向 */
  orderDir?: 'asc' | 'desc';
}

// ==================== API 响应类型 ====================

/**
 * 告警列表响应
 */
export interface AlertSignalListResponse {
  /** 告警数组 */
  items: AlertSignal[];
  /** 总数 */
  total: number;
  /** 当前页码 */
  page: number;
  /** 每页数量 */
  pageSize: number;
}

// ==================== 常量定义 ====================

/**
 * 触发类型选项
 * 用于下拉选择框
 */
export const ALERT_TRIGGER_TYPE_OPTIONS: { label: string; value: AlertTriggerType }[] = [
  { label: '仅一次 (once_only)', value: 'once_only' },
  { label: '每根K线 (each_kline)', value: 'each_kline' },
  { label: '每根K线收盘 (each_kline_close)', value: 'each_kline_close' },
  { label: '每分钟 (each_minute)', value: 'each_minute' },
];

/**
 * 策略类型选项
 * 用于下拉选择框
 */
export const ALERT_STRATEGY_TYPE_OPTIONS: { label: string; value: AlertStrategyType }[] = [
  { label: 'MACD共振策略V5', value: 'MACDResonanceStrategyV5' },
  { label: 'MACD共振策略V6', value: 'MACDResonanceStrategyV6' },
  { label: 'MACD做空策略', value: 'MACDResonanceShortStrategy' },
  { label: 'Alpha01策略', value: 'Alpha01Strategy' },
  { label: 'MACD策略 (macd)', value: 'macd' },
  { label: '随机策略 (random)', value: 'random' },
];

/**
 * 默认告警 MACD 参数
 */
export const DEFAULT_ALERT_MACD_PARAMS: AlertMacdParams = {
  fast1: 12,
  slow1: 26,
  signal1: 9,
  fast2: 5,
  slow2: 10,
  signal2: 4,
};

/**
 * 默认告警参数
 */
export const DEFAULT_ALERT_PARAMS: AlertParams = {
  fast_period: 12,
  slow_period: 26,
  signal_period: 9,
  threshold: 0,
};

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
];

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
];
