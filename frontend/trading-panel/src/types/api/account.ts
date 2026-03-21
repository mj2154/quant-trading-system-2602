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

