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
 * 现货账户信息
 *
 * 对应后端 SpotAccountInfo
 */
export interface SpotAccountInfo {
  /** 挂单手续费率 */
  makerCommission: number | string
  /** 吃单手续费率 */
  takerCommission: number | string
  /** 买入手续费率 */
  buyerCommission: number | string
  /** 卖出手续费率 */
  sellerCommission: number | string
  /** 手续费率详情 */
  commissionRates: SpotCommissionRates | null
  /** 是否可以交易 */
  canTrade: boolean
  /** 是否可以提现 */
  canWithdraw: boolean
  /** 是否可以充值 */
  canDeposit: boolean
  /** 是否是经纪商 */
  brokered: boolean
  /** 是否需要自成交预防 */
  requireSelfTradePrevention: boolean
  /** 是否阻止 SOR */
  preventSor: boolean
  /** 更新时间 */
  updateTime: number
  /** 账户类型 */
  accountType: string
  /** 余额列表 */
  balances: SpotBalance[]
  /** 权限列表 */
  permissions: string[]
  /** 用户ID */
  uid?: number
}

// ==================== 期货账户类型 ====================

/**
 * 期货资产信息
 *
 * 对应后端 FuturesAsset
 */
export interface FuturesAsset {
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
 * 对应后端 FuturesPosition
 */
export interface FuturesPosition {
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
  /** 更新时间 */
  updateTime?: number
}

/**
 * 期货账户信息
 *
 * 对应后端 FuturesAccountInfo (V3 API)
 */
export interface FuturesAccountInfo {
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
  totalCrossUnrealizedProfit?: string
  /** 可用余额 */
  availableBalance?: string
  /** 最大可转出余额 */
  maxWithdrawAmount?: string
  /** 更新时间 */
  updateTime?: number
  /** 资产列表 */
  assets: FuturesAsset[]
  /** 持仓列表 */
  positions: FuturesPosition[]
}

// ==================== 统一账户类型 ====================

/**
 * 账户信息（统一格式）
 */
export interface AccountInfo {
  /** 账户类型 */
  accountType: 'spot' | 'futures'
  /** 账户信息数据 */
  accountInfo: SpotAccountInfo | FuturesAccountInfo
  /** 更新时间 */
  updateTime?: number
}

/**
 * 账户请求响应
 */
export interface AccountResponse {
  /** 账户类型标识 */
  type: string
  /** 账户信息内容 */
  content: SpotAccountInfo | FuturesAccountInfo
  /** 更新时间 */
  updateTime?: number
}

// ==================== 账户余额模型 ====================

/**
 * 账户余额模型
 *
 * 对应后端 AccountBalance
 */
export interface AccountBalance {
  /** 资产名称 */
  asset: string
  /** 可用数量 */
  free: number
  /** 冻结数量 */
  locked: number
  /** 总数量 */
  total: number
}

// ==================== 持仓信息模型 ====================

/**
 * 持仓信息模型
 *
 * 对应后端 PositionInfo
 */
export interface PositionInfo {
  /** 交易对 */
  symbol: string
  /** 持仓方向: LONG, SHORT, BOTH */
  positionSide: string
  /** 持仓数量 */
  positionAmount: number
  /** 开仓价格 */
  entryPrice: number
  /** 标记价格 */
  markPrice: number
  /** 未实现盈亏 */
  unrealizedPnl: number
  /** 杠杆倍数 */
  leverage: number
  /** 保证金 */
  margin: number
  /** 盈亏百分比 */
  pnlPercent: number
}

// ==================== 前端展示类型 ====================

/**
 * 账户概览（用于展示）
 */
export interface AccountOverview {
  /** 账户类型 */
  accountType: 'spot' | 'futures'
  /** 总资产（USDT估值） */
  totalAsset: string
  /** 可用余额 */
  availableBalance: string
  /** 持仓数量 */
  positionCount: number
  /** 更新时间 */
  updateTime: string
}

/**
 * 持仓项目（用于展示）
 */
export interface PositionItem {
  /** 交易对 */
  symbol: string
  /** 持仓方向 */
  side: 'long' | 'short' | 'both'
  /** 持仓数量 */
  amount: string
  /** 开仓价格 */
  entryPrice: string
  /** 标记价格 */
  markPrice: string
  /** 未实现盈亏 */
  unrealizedPnl: string
  /** 持仓保证金 */
  margin: string
  /** 强平价格 */
  liquidationPrice?: string
  /** 名义价值 */
  notional?: string
  /** 杠杆倍数 */
  leverage?: string
  /** 是否逐仓 */
  isIsolated?: boolean
}

/**
 * 余额项目（用于展示）
 */
export interface BalanceItem {
  /** 资产 */
  asset: string
  /** 可用 */
  free: string
  /** 锁定 */
  locked: string
  /** 总计 */
  total: string
}
