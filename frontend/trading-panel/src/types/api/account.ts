/**
 * 账户数据类型 - 对应后端 account_models.py
 *
 * 使用 camelCase 与 WebSocket 协议保持一致
 * 后端使用 CamelCaseModel 序列化，自动转为 camelCase
 */

// ==================== 现货账户类型 ====================

/**
 * 现货余额信息
 */
export interface SpotBalance {
  /** 资产名称 */
  asset: string
  /** 可用数量 */
  free: string
  /** 锁定数量 */
  locked: string
}

/**
 * 现货手续费率
 */
export interface SpotCommissionRates {
  /** 挂单手续费率 */
  maker: string
  /** 吃单手续费率 */
  taker: string
  /** 买入手续费率 */
  buyer: string
  /** 卖出手续费率 */
  seller: string
}

/**
 * 现货账户详情
 *
 * 对应后端 SpotAccountDetail
 * 设计文档: 08-api-models.md
 */
export interface SpotAccountDetail {
  /** 挂单手续费率 */
  makerCommission?: number
  /** 吃单手续费率 */
  takerCommission?: number
  /** 买入手续费率 */
  buyerCommission?: number
  /** 卖出手续费率 */
  sellerCommission?: number
  /** 手续费率详情 */
  commissionRates?: SpotCommissionRates | null
  /** 是否可以交易 */
  canTrade?: boolean
  /** 是否可以提现 */
  canWithdraw?: boolean
  /** 是否可以充值 */
  canDeposit?: boolean
  /** 是否是经纪商 */
  brokered?: boolean
  /** 是否需要自成交预防 */
  requireSelfTradePrevention?: boolean
  /** 是否阻止 SOR */
  preventSor?: boolean
  /** 更新时间 */
  updateTime?: number
  /** 账户类型 */
  accountType?: string
  /** 余额列表 */
  balances?: SpotBalance[]
  /** 权限列表 */
  permissions?: string[]
  /** 用户ID */
  uid?: number
  /** 速率限制信息 */
  rateLimits?: Record<string, unknown>[]
}

/**
 * 现货账户数据（外层包装）
 *
 * 对应后端 SpotAccountData
 * 设计文档: 08-api-models.md
 */
export interface SpotAccountData {
  /** 账户类型 */
  accountType: string
  /** 账户详情 */
  account: SpotAccountDetail
}

// ==================== 期货账户类型 ====================

/**
 * 期货资产信息
 *
 * 对应后端 FuturesAccountAsset
 */
export interface FuturesAccountAsset {
  /** 资产名称 */
  asset: string
  /** 钱包余额 */
  walletBalance?: string
  /** 未实现盈亏 */
  unrealizedProfit?: string
  /** 保证金余额 */
  marginBalance?: string
  /** 维持保证金 */
  maintMargin?: string
  /** 当前所需起始保证金 */
  initialMargin?: string
  /** 持仓所需起始保证金 */
  positionInitialMargin?: string
  /** 当前挂单所需起始保证金 */
  openOrderInitialMargin?: string
  /** 全仓账户余额 */
  crossWalletBalance?: string
  /** 全仓持仓未实现盈亏 */
  crossUnrealizedProfit?: string
  /** 可用余额 */
  availableBalance?: string
  /** 最大可转出余额 */
  maxWithdrawAmount?: string
  /** 保证金是否可用 */
  marginAvailable?: boolean
  /** 更新时间 */
  updateTime?: number
}

/**
 * 期货持仓信息
 *
 * 对应后端 FuturesAccountPosition
 */
export interface FuturesAccountPosition {
  /** 交易对 */
  symbol: string
  /** 持仓方向: BOTH, LONG, SHORT */
  positionSide?: string
  /** 持仓数量 */
  positionAmt?: string
  /** 未实现盈亏 */
  unrealizedProfit?: string
  /** 逐仓保证金 */
  isolatedMargin?: string
  /** 名义价值 */
  notional?: string
  /** 逐仓钱包余额 */
  isolatedWallet?: string
  /** 持仓所需起始保证金 */
  initialMargin?: string
  /** 维持保证金 */
  maintMargin?: string
  /** 杠杆倍数 */
  leverage?: number
  /** 更新时间 */
  updateTime?: number
}

/**
 * 期货账户详情
 *
 * 对应后端 FuturesAccountDetail (V3 API)
 * 设计文档: 08-api-models.md
 */
export interface FuturesAccountDetail {
  /** 账户总起始保证金 */
  totalInitialMargin?: string
  /** 账户总维持保证金 */
  totalMaintMargin?: string
  /** 账户总钱包余额 */
  totalWalletBalance?: string
  /** 账户总未实现盈亏 */
  totalUnrealizedProfit?: string
  /** 账户总保证金余额 */
  totalMarginBalance?: string
  /** 持仓所需起始保证金 */
  totalPositionInitialMargin?: string
  /** 当前挂单所需起始保证金 */
  totalOpenOrderInitialMargin?: string
  /** 全仓钱包余额 */
  totalCrossWalletBalance?: string
  /** 全仓未实现盈亏 */
  totalCrossUnPnl?: string
  /** 可用余额 */
  availableBalance?: string
  /** 最大可转出余额 */
  maxWithdrawAmount?: string
  /** 账户手续费等级 */
  feeTier?: number
  /** 是否开启手续费折扣 */
  feeBurn?: boolean
  /** 是否为多资产模式 */
  multiAssetsMargin?: boolean
  /** 交易组ID */
  tradeGroupId?: number
  /** 更新时间 */
  updateTime?: number
  /** 资产列表 */
  assets: FuturesAccountAsset[]
  /** 持仓列表 */
  positions: FuturesAccountPosition[]
  /** 速率限制信息 */
  rateLimits?: Record<string, unknown>[]
}

/**
 * 期货账户数据（外层包装）
 *
 * 对应后端 FuturesAccountData
 * 设计文档: 08-api-models.md
 */
export interface FuturesAccountData {
  /** 账户类型 */
  accountType: string
  /** 账户详情 */
  account: FuturesAccountDetail
}

// ==================== 账户增量更新类型（WS订阅） ====================
// 后端使用 alias 输出币安原始短字段名，参考 account_models.py
// 消息结构: { type: "UPDATE", timestamp, subscriptionKey, data }

/**
 * 现货余额更新
 *
 * 对应后端 SpotBalanceUpdate
 * 对应 outboundAccountPosition 事件中的 B 字段
 * 使用币安原始短字段名
 */
export interface SpotBalanceUpdate {
  /** 资产名称 (alias: a) */
  a: string
  /** 可用余额 (alias: f) */
  f: string
  /** 冻结余额 (alias: l) */
  l: string
}

/**
 * 现货账户增量推送
 *
 * 对应后端 SpotAccountUpdate
 * 对应 WS协议 outboundAccountPosition 事件
 * 使用 alias 输出币安原始短字段名
 * 设计文档: 08-api-models.md
 *
 * 消息格式（实际收到的字段名）:
 * {
 *   "e": "outboundAccountPosition",
 *   "E": 1564034571105,
 *   "u": 1564034571073,
 *   "B": [{ "a": "BTC", "f": "1.0", "l": "0.5" }]
 * }
 */
export interface SpotAccountUpdate {
  /** 事件类型 (alias: e) */
  e: string
  /** 事件时间 (alias: E) */
  E: number
  /** 账户最后更新时间 (alias: u) */
  u: number
  /** 余额列表 (alias: B) */
  B: SpotBalanceUpdate[]
}

/**
 * 现货余额更新事件
 *
 * 对应后端 SpotBalanceUpdateEvent
 * 对应 WS协议 balanceUpdate 事件
 * 设计文档: 08-api-models.md
 *
 * 消息格式:
 * {
 *   "e": "balanceUpdate",
 *   "E": 1564034571105,
 *   "a": "BTC",
 *   "d": "1.0",
 *   "T": 1564034571000
 * }
 */
export interface SpotBalanceUpdateEvent {
  /** 事件类型 (alias: e) */
  e: string
  /** 事件时间 (alias: E) */
  E: number
  /** 资产名称 (alias: a) */
  a: string
  /** 余额变化量 (alias: d) */
  d: string
  /** 清算时间 (alias: T) */
  T: number
}

/**
 * 现货订单执行报告事件
 *
 * 对应后端 SpotExecutionReportEvent
 * 对应 WS协议 executionReport 事件
 * 设计文档: 08-api-models.md
 */
export interface SpotExecutionReportEvent {
  /** 事件类型 (alias: e) */
  e: string
  /** 事件时间 (alias: E) */
  E: number
  /** 交易对 (alias: s) */
  s: string
  /** 客户端订单ID (alias: c) */
  c: string
  /** 订单方向 (alias: S) */
  S: string
  /** 订单类型 (alias: o) */
  o: string
  /** 订单状态 (alias: X) */
  X: string
  /** 订单ID (alias: i) */
  i?: number
  /** 订单数量 (alias: q) */
  q?: string
  /** ... 更多字段见后端模型 */
}

/**
 * 期货账户配置更新 - 杠杆
 *
 * 对应后端 FuturesAccountConfigLeverageUpdate
 * 对应 ACCOUNT_CONFIG_UPDATE 事件的 ac 字段
 */
export interface FuturesAccountConfigLeverageUpdate {
  /** 交易对符号 (alias: s) */
  s: string
  /** 杠杆倍数 (alias: l) */
  l: number
}

/**
 * 期货账户配置更新 - 多资产模式
 *
 * 对应后端 FuturesAccountConfigMultiAssetUpdate
 * 对应 ACCOUNT_CONFIG_UPDATE 事件的 ai 字段
 */
export interface FuturesAccountConfigMultiAssetUpdate {
  /** 多资产模式 (alias: j) */
  j: boolean
}

/**
 * 期货账户配置更新
 *
 * 对应后端 FuturesAccountConfigUpdate
 * 对应 WS协议 ACCOUNT_CONFIG_UPDATE 事件
 *
 * 消息格式:
 * {
 *   "e": "ACCOUNT_CONFIG_UPDATE",
 *   "E": 1611646737479,
 *   "T": 1611646737476,
 *   "ac": { "s": "BTCUSDT", "l": 25 },   // 杠杆配置（可选）
 *   "ai": { "j": true }                   // 多资产模式（可选）
 * }
 */
export interface FuturesAccountConfigUpdate {
  /** 事件类型 (alias: e) */
  e: string
  /** 事件时间 (alias: E) */
  E: number
  /** 事务时间 (alias: T) */
  T: number
  /** 杠杆配置更新 (alias: ac) */
  ac?: FuturesAccountConfigLeverageUpdate
  /** 多资产模式更新 (alias: ai) */
  ai?: FuturesAccountConfigMultiAssetUpdate
}

/**
 * 期货账户更新内容
 *
 * 对应后端 FuturesAccountUpdateContent
 * 对应 ACCOUNT_UPDATE 事件的 a 字段内容
 * 使用币安原始短字段名
 *
 * 消息格式（实际收到的字段名）:
 * {
 *   "e": "ACCOUNT_UPDATE",
 *   "E": 1564034571105,
 *   "T": 1564034571000,
 *   "a": {
 *     "m": "ORDER",
 *     "B": [...],  // 余额更新
 *     "P": [...]   // 持仓更新
 *   }
 * }
 */
export interface FuturesAccountUpdateContent {
  /** 变动原因 (alias: m) */
  m?: string
  /** 余额更新列表 (alias: B) */
  B?: FuturesBalanceUpdate[]
  /** 持仓更新列表 (alias: P) */
  P?: FuturesPositionUpdate[]
}

/**
 * 期货账户余额更新
 *
 * 对应 BinanceFuturesAccountUpdateBalanceModel
 * 使用币安原始短字段名
 */
export interface FuturesBalanceUpdate {
  /** 资产名称 (alias: a) */
  a: string
  /** 钱包余额 (alias: wb) */
  wb: string
  /** 全仓钱包余额 (alias: cw) */
  cw: string
  /** 余额变动 (alias: bc) */
  bc: string
  /** 变动原因 (alias: m) */
  m?: string
}

/**
 * 期货账户持仓更新
 *
 * 对应 BinanceFuturesAccountUpdatePositionModel
 * 使用币安原始短字段名
 */
export interface FuturesPositionUpdate {
  /** 交易对 (alias: s) */
  s: string
  /** 持仓数量 (alias: pa) */
  pa: string
  /** 开仓价格 (alias: ep) */
  ep: string
  /** 盈亏平衡价格 (alias: bep) */
  bep?: string
  /** 累计已实现盈亏 (alias: cr) */
  cr?: string
  /** 未实现盈亏 (alias: up) */
  up?: string
  /** 保证金类型 (alias: mt) */
  mt?: string
  /** 逐仓钱包余额 (alias: iw) */
  iw?: string
  /** 持仓方向 (alias: ps) */
  ps: string
}

/**
 * 期货账户更新数据
 *
 * 对应 ACCOUNT_UPDATE 事件的 a 字段内容
 * 使用币安原始短字段名
 */
export interface FuturesAccountUpdateData {
  /** 更新原因 (alias: m) */
  m?: string
  /** 余额更新列表 (alias: B) */
  B?: FuturesBalanceUpdate[]
  /** 持仓更新列表 (alias: P) */
  P?: FuturesPositionUpdate[]
}

/**
 * 期货账户增量推送
 *
 * 对应后端 FuturesAccountUpdate
 * 对应 WS协议 ACCOUNT_UPDATE 事件
 * 直接使用币安原始短字段名 e, E, T, a
 *
 * 消息格式（实际收到的字段名）:
 * {
 *   "e": "ACCOUNT_UPDATE",
 *   "E": 1564034571105,
 *   "T": 1564034571000,
 *   "a": {
 *     "m": "ORDER",
 *     "B": [...],
 *     "P": [...]
 *   }
 * }
 */
export interface FuturesAccountUpdate {
  /** 事件类型 (alias: e) */
  e: string
  /** 事件时间 (alias: E) */
  E: number
  /** 事务时间 (alias: T) */
  T: number
  /** 更新数据 (alias: a) */
  a: FuturesAccountUpdateData
}

// ==================== 期货订单成交更新 (ORDER_TRADE_UPDATE) ====================

/**
 * 期货订单成交更新 (ORDER_TRADE_UPDATE事件)
 *
 * 对应后端 FuturesOrderTradeUpdate
 * 消息格式:
 * {
 *   "e": "ORDER_TRADE_UPDATE",
 *   "E": 1568016084706,
 *   "T": 1568016084650,
 *   "o": { ... }
 * }
 */
export interface FuturesOrderTradeUpdate {
  /** 事件类型 (alias: e) */
  e: string
  /** 事件时间 (alias: E) */
  E: number
  /** 事务时间 (alias: T) */
  T: number
  /** 订单数据 (alias: o) */
  o: Record<string, unknown>
}

// ==================== 期货简化交易事件 (TRADE_LITE) ====================

/**
 * 期货简化交易事件 (TRADE_LITE事件)
 *
 * 对应后端 FuturesTradeLiteEvent
 * 消息格式:
 * {
 *   "e": "TRADE_LITE",
 *   "E": 1568016084706,
 *   "T": 1568016084650,
 *   "s": "BTCUSDT",
 *   "t": 12345,
 *   "i": 67890,
 *   "p": "9000.00",
 *   "q": "1.00",
 *   "S": "BUY",
 *   "m": false,
 *   "c": "client_order_id",
 *   "L": "9000.00",
 *   "l": "1.00"
 * }
 */
export interface FuturesTradeLiteEvent {
  /** 事件类型 (alias: e) */
  e: string
  /** 事件时间 (alias: E) */
  E: number
  /** 事务时间 (alias: T) */
  T: number
  /** 交易对 (alias: s) */
  s: string
  /** 成交ID (alias: t) */
  t: number
  /** 订单ID (alias: i) */
  i: number
  /** 原始价格 (alias: p) */
  p: string
  /** 原始数量 (alias: q) */
  q: string
  /** 订单方向 (alias: S) */
  S: 'BUY' | 'SELL'
  /** 是否做市商 (alias: m) */
  m: boolean
  /** 客户端订单ID (alias: c) */
  c: string
  /** 最近成交价格 (alias: L) */
  L: string
  /** 最近成交数量 (alias: l) */
  l: string
}

// ==================== 期货保证金追缴 (MARGIN_CALL) ====================

/**
 * 期货保证金追缴持仓项
 *
 * 对应 BinanceFuturesMarginCallPositionModel
 */
export interface FuturesMarginCallPosition {
  /** 交易对 (alias: s) */
  s: string
  /** 持仓方向 (alias: ps) */
  ps: 'LONG' | 'SHORT' | 'BOTH'
  /** 持仓数量 (alias: pa) */
  pa: string
  /** 保证金类型 (alias: mt) */
  mt: 'cross' | 'isolated'
  /** 逐仓钱包 (alias: iw) */
  iw: string
  /** 标记价格 (alias: mp) */
  mp: string
  /** 未实现盈亏 (alias: up) */
  up: string
  /** 维持保证金要求 (alias: mm) */
  mm: string
}

/**
 * 期货保证金追缴事件 (MARGIN_CALL)
 *
 * 对应 BinanceFuturesMarginCallWSModel
 * 消息格式:
 * {
 *   "e": "MARGIN_CALL",
 *   "E": 1568016084706,
 *   "cw": "1000.00",
 *   "p": [...]
 * }
 */
export interface FuturesMarginCall {
  /** 事件类型 (alias: e) */
  e: string
  /** 事件时间 (alias: E) */
  E: number
  /** 跨账户钱包余额 (alias: cw) */
  cw: string
  /** 追缴持仓列表 (alias: p) */
  p: FuturesMarginCallPosition[]
}

// ==================== 期货条件单更新 (ALGO_UPDATE) ====================

/**
 * 期货条件单数据
 *
 * 对应 BinanceFuturesAlgoOrderDataModel
 */
export interface FuturesAlgoOrderData {
  /** 客户端算法订单ID (alias: caid) */
  caid: string
  /** 算法订单ID (alias: aid) */
  aid: number
  /** 算法类型 (alias: at) */
  at: string
  /** 订单类型 (alias: o) */
  o: string
  /** 交易对 (alias: s) */
  s: string
  /** 订单方向 (alias: S) */
  S: 'BUY' | 'SELL'
  /** 持仓方向 (alias: ps) */
  ps: 'LONG' | 'SHORT' | 'BOTH'
  /** 有效期限 (alias: f) */
  f: string
  /** 数量 (alias: q) */
  q: string
  /** 算法订单状态 (alias: X) */
  X: string
  /** 算法订单ID (alias: ai) */
  ai: string
  /** 平均成交价格 (alias: ap) */
  ap: string
  /** 已成交数量 (alias: aq) */
  aq: string
  /** 实际订单类型 (alias: act) */
  act: string
  /** 触发价格 (alias: tp) */
  tp: string
  /** 订单价格 (alias: p) */
  p: string
  /** STP模式 (alias: V) */
  V: string
  /** 工作类型 (alias: wt) */
  wt: string
  /** 价格匹配模式 (alias: pm) */
  pm: string
  /** 是否全平 (alias: cp) */
  cp: boolean
  /** 是否开启价格保护 (alias: pP) */
  pP: boolean
  /** 是否仅减仓 (alias: R) */
  R: boolean
  /** 触发时间 (alias: tt) */
  tt: number
  /** GTD有效期 (alias: gtd) */
  gtd: number
  /** 拒绝原因 (alias: rm) */
  rm: string
}

/**
 * 期货条件单更新事件 (ALGO_UPDATE)
 *
 * 对应 BinanceFuturesAlgoUpdateWSModel
 * 消息格式:
 * {
 *   "e": "ALGO_UPDATE",
 *   "T": 1568016084650,
 *   "E": 1568016084706,
 *   "o": { ... }
 * }
 */
export interface FuturesAlgoUpdate {
  /** 事件类型 (alias: e) */
  e: string
  /** 事务时间 (alias: T) */
  T: number
  /** 事件时间 (alias: E) */
  E: number
  /** 订单数据 (alias: o) */
  o: FuturesAlgoOrderData
}

// ==================== 期货策略更新 (STRATEGY_UPDATE) ====================

/**
 * 期货策略数据
 *
 * 对应 BinanceFuturesStrategyUpdateDataModel
 */
export interface FuturesStrategyData {
  /** 策略ID (alias: si) */
  si: number
  /** 策略类型 (alias: st) */
  st: string
  /** 策略状态 (alias: ss) */
  ss: string
  /** 交易对 (alias: s) */
  s: string
  /** 更新时间 (alias: ut) */
  ut: number
  /** 操作代码 (alias: c) */
  c: number
}

/**
 * 期货策略更新事件 (STRATEGY_UPDATE)
 *
 * 对应 BinanceFuturesStrategyUpdateWSModel
 * 消息格式:
 * {
 *   "e": "STRATEGY_UPDATE",
 *   "T": 1568016084650,
 *   "E": 1568016084706,
 *   "su": { ... }
 * }
 */
export interface FuturesStrategyUpdate {
  /** 事件类型 (alias: e) */
  e: string
  /** 事务时间 (alias: T) */
  T: number
  /** 事件时间 (alias: E) */
  E: number
  /** 策略数据 (alias: su) */
  su: FuturesStrategyData
}

// ==================== 期货网格更新 (GRID_UPDATE) ====================

/**
 * 期货网格数据
 *
 * 对应 BinanceFuturesGridUpdateDataModel
 */
export interface FuturesGridData {
  /** 策略ID (alias: si) */
  si: number
  /** 策略类型 (alias: st) */
  st: string
  /** 策略状态 (alias: ss) */
  ss: string
  /** 交易对 (alias: s) */
  s: string
  /** 已实现盈亏 (alias: r) */
  r: string
  /** 未成交平均价格 (alias: up) */
  up: string
  /** 未成交数量 (alias: uq) */
  uq: string
  /** 未成交手续费 (alias: uf) */
  uf: string
  /** 已匹配盈亏 (alias: mp) */
  mp: string
  /** 更新时间 (alias: ut) */
  ut: number
}

/**
 * 期货网格更新事件 (GRID_UPDATE)
 *
 * 对应 BinanceFuturesGridUpdateWSModel
 * 消息格式:
 * {
 *   "e": "GRID_UPDATE",
 *   "T": 1568016084650,
 *   "E": 1568016084706,
 *   "gu": { ... }
 * }
 */
export interface FuturesGridUpdate {
  /** 事件类型 (alias: e) */
  e: string
  /** 事务时间 (alias: T) */
  T: number
  /** 事件时间 (alias: E) */
  E: number
  /** 网格数据 (alias: gu) */
  gu: FuturesGridData
}

// ==================== 期货条件单触发拒绝 (CONDITIONAL_ORDER_TRIGGER_REJECT) ====================

/**
 * 期货条件单拒绝数据
 *
 * 对应 BinanceFuturesConditionalOrderRejectDataModel
 */
export interface FuturesConditionalOrderRejectData {
  /** 交易对 (alias: s) */
  s: string
  /** 订单ID (alias: i) */
  i: number
  /** 拒绝原因 (alias: r) */
  r: string
}

/**
 * 期货条件单触发拒绝事件 (CONDITIONAL_ORDER_TRIGGER_REJECT)
 *
 * 对应 BinanceFuturesConditionalOrderTriggerRejectWSModel
 * 消息格式:
 * {
 *   "e": "CONDITIONAL_ORDER_TRIGGER_REJECT",
 *   "E": 1568016084706,
 *   "T": 1568016084650,
 *   "or": { ... }
 * }
 */
export interface FuturesConditionalOrderTriggerReject {
  /** 事件类型 (alias: e) */
  e: string
  /** 事件时间 (alias: E) */
  E: number
  /** 事务时间 (alias: T) */
  T: number
  /** 拒绝数据 (alias: or) */
  or: FuturesConditionalOrderRejectData
}

/**
 * 统一账户更新 WS 消息格式
 *
 * 对应后端 MessageUpdate 消息
 * 外层结构: { type, timestamp, subscriptionKey, data }
 *
 * data 类型根据 subscriptionKey 区分:
 * - "BINANCE:SPOT@USERDATA" -> SpotAccountUpdate | SpotBalanceUpdateEvent | SpotExecutionReportEvent
 * - "BINANCE:FUTURES@USERDATA" -> 多种期货事件类型
 */
export interface AccountUpdateMessage {
  /** 消息类型 (固定值 "UPDATE") */
  type: 'UPDATE'
  /** 时间戳 */
  timestamp: number
  /** 订阅键 */
  subscriptionKey: string
  /** 更新内容 */
  data: AccountUpdate
}

/**
 * 统一账户更新类型（兼容期货和现货）
 *
 * 用于 SubscriptionData 联合类型
 * 注意：此类型是 WS 消息中的 content 部分
 */
export type AccountUpdate =
  | SpotAccountUpdate
  | FuturesAccountUpdate
  | SpotBalanceUpdateEvent
  | SpotExecutionReportEvent
  | FuturesAccountConfigUpdate
  | FuturesOrderTradeUpdate
  | FuturesTradeLiteEvent
  | FuturesMarginCall
  | FuturesAlgoUpdate
  | FuturesStrategyUpdate
  | FuturesGridUpdate
  | FuturesConditionalOrderTriggerReject

