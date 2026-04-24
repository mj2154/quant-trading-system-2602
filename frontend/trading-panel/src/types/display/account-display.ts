/**
 * 账户显示模型 - UI专用数据类型
 *
 * 这些类型专门用于前端UI展示，与币安API原始数据分离。
 * 通过Converter将API数据转换为显示模型，确保UI只依赖显示模型。
 *
 * 设计原则:
 * - 显示模型是不可变的，每次更新返回新对象
 * - 聚合字段在转换时计算，而非每次computed重新计算
 * - WS增量更新只修改变化的字段
 */

// ==================== 现货账户显示模型 ====================

/**
 * 现货余额显示项
 */
export interface SpotBalanceDisplay {
  /** 资产名称 */
  asset: string
  /** 可用数量 */
  free: string
  /** 锁定数量 */
  locked: string
  /** 总数量 (free + locked) */
  total: string
}

/**
 * 现货手续费率
 */
export interface SpotCommissionRatesDisplay {
  maker: string
  taker: string
  buyer: string
  seller: string
}

/**
 * 现货账户显示模型 - UI专用
 */
export interface SpotAccountDisplay {
  // 账户概览
  /** 总资产(折算USDT，简化版仅统计USDT余额) */
  totalAsset: string
  /** 可用余额 */
  availableBalance: string
  /** 锁定余额 */
  lockedBalance: string

  // 账户权限状态
  /** 是否可以交易 */
  canTrade: boolean
  /** 是否可以提现 */
  canWithdraw: boolean
  /** 是否可以充值 */
  canDeposit: boolean

  // 账户类型
  accountType: string

  // 用户ID
  uid: number

  // 账户配置
  brokered: boolean
  requireSelfTradePrevention: boolean
  preventSor: boolean

  // 手续费率
  makerCommission: number
  takerCommission: number
  buyerCommission: number
  sellerCommission: number
  commissionRates: SpotCommissionRatesDisplay | null

  // 权限列表
  permissions: string[]

  // 余额列表
  balances: SpotBalanceDisplay[]

  /** 更新时间戳 */
  updateTime: number
}

// ==================== 期货账户显示模型 ====================

/**
 * 期货资产显示项
 */
export interface FuturesAssetDisplay {
  /** 资产名称 (USDT, USDC, BNB等) */
  asset: string
  /** 钱包余额 */
  walletBalance: string
  /** 未实现盈亏 */
  unrealizedProfit: string
  /** 保证金余额 */
  marginBalance: string
  /** 可用余额 */
  availableBalance: string
  /** 最大可转出 */
  maxWithdraw: string
  /** 全仓钱包余额 */
  crossWalletBalance: string
  /** 全仓未实现盈亏 */
  crossUnrealizedProfit: string
  /** 更新时间戳 */
  updateTime?: number
}

/**
 * 期货持仓显示项
 *
 * 注意: WS推送的ACCOUNT_UPDATE不包含entryPrice, markPrice, liquidationPrice, leverage
 * 这些字段只在初始GET /fapi/v3/account获取，之后通过WS更新只更新pa和up
 */
export interface FuturesPositionDisplay {
  /** 交易对 */
  symbol: string
  /** 持仓方向 */
  side: 'LONG' | 'SHORT' | 'BOTH'
  /** 持仓数量 */
  positionAmt: string
  /** 未实现盈亏 */
  unrealizedProfit: string

  // 字段数据来源说明:
  // - entryPrice: WS推送 (ACCOUNT_UPDATE事件P字段的ep)
  // - markPrice: WS推送 (MARGIN_CALL事件p字段的mp)
  // - liquidationPrice: 无WS来源，需通过/fapi/v3/positionRisk获取（暂不支持）
  // - maintMargin: WS推送 (MARGIN_CALL事件p字段的mm)
  /** 开仓价格 */
  entryPrice: string
  /** 标记价格 */
  markPrice: string
  /** 强平价格 */
  liquidationPrice: string
  /** 杠杆倍数 */
  leverage: number

  // 保证金信息
  /** 逐仓保证金 */
  isolatedMargin: string
  /** 起始保证金 */
  initialMargin: string
  /** 维持保证金 */
  maintMargin: string
  /** 名义价值 */
  notional: string

  /** 更新时间戳 */
  updateTime: number
}

/**
 * 期货持仓模式
 * - oneWay: 单向模式（只能有一个方向）
 * - hedge: 对冲模式（可以同时有多空两个方向）
 */
export type FuturesPositionMode = 'oneWay' | 'hedge'

/**
 * 期货账户显示模型 - UI专用
 */
export interface FuturesAccountDisplay {
  // 账户概览 (基于USDT资产汇总)
  /** 总钱包余额 */
  totalWalletBalance: string
  /** 总未实现盈亏 */
  totalUnrealizedProfit: string
  /** 总保证金余额 */
  totalMarginBalance: string
  /** 可用余额 */
  availableBalance: string
  /** 最大可转出 */
  maxWithdrawAmount: string

  // 保证金相关
  /** 账户总起始保证金 */
  totalInitialMargin: string
  /** 账户总维持保证金 */
  totalMaintMargin: string
  /** 持仓所需起始保证金 */
  totalPositionInitialMargin: string
  /** 当前挂单所需起始保证金 */
  totalOpenOrderInitialMargin: string

  // 账户信息
  /** 手续费等级 */
  feeTier: number
  /** 是否多资产模式 */
  multiAssetsMargin: boolean
  /** 持仓模式 - 单向/对冲 */
  positionMode: FuturesPositionMode

  // 资产和持仓列表
  assets: FuturesAssetDisplay[]
  positions: FuturesPositionDisplay[]

  /** 更新时间戳 */
  updateTime: number
}

// ==================== 统一账户显示模型 ====================

/**
 * 账户显示模型 - 统一入口
 */
export interface AccountDisplay {
  spot: SpotAccountDisplay
  futures: FuturesAccountDisplay
}
