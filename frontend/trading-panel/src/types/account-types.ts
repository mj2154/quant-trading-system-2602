/**
 * 账户信息类型定义
 *
 * 对应后端期货和现货账户信息数据模型
 * 使用 camelCase 与 WebSocket 协议保持一致
 */

// ==================== 现货账户类型 ====================

/**
 * 现货余额信息
 */
export interface SpotBalance {
  asset: string
  free: string
  locked: string
}

/**
 * 现货手续费率
 */
export interface SpotCommissionRates {
  maker: string
  taker: string
  buyer: string
  seller: string
}

/**
 * 现货账户信息
 */
export interface SpotAccountInfo {
  makerCommission: number | string
  takerCommission: number | string
  buyerCommission: number | string
  sellerCommission: number | string
  commissionRates: SpotCommissionRates | null
  canTrade: boolean
  canWithdraw: boolean
  canDeposit: boolean
  brokered: boolean
  requireSelfTradePrevention: boolean
  preventSor: boolean
  updateTime: number
  accountType: string
  balances: SpotBalance[]
  permissions: string[]
  uid?: number
}

// ==================== 期货账户类型 ====================

/**
 * 期货资产信息
 *
 * 对应 /fapi/v3/account 响应中的 assets 数组元素
 * 使用 camelCase 与 API 响应保持一致
 */
export interface FuturesAsset {
  asset: string                    // 资产名称
  walletBalance?: string          // 钱包余额
  unrealizedProfit?: string       // 未实现盈亏
  marginBalance?: string          // 保证金余额
  maintMargin?: string            // 维持保证金
  initialMargin?: string          // 当前所需起始保证金
  positionInitialMargin?: string // 持仓所需起始保证金(基于最新标记价格)
  openOrderInitialMargin?: string // 当前挂单所需起始保证金
  crossWalletBalance?: string   // 全仓账户余额
  crossUnrealizedProfit?: string // 全仓持仓未实现盈亏
  availableBalance?: string       // 可用余额
  maxWithdrawAmount?: string     // 最大可转出余额
  marginAvailable?: boolean       // 保证金是否可用
  updateTime?: number             // 更新时间
}

/**
 * 期货持仓信息
 *
 * 对应 /fapi/v3/account 响应中的 positions 数组元素
 * 字段与币安官方文档完全一致
 * 使用 camelCase 与 API 响应保持一致
 */
export interface FuturesPosition {
  symbol: string              // 交易对
  positionSide?: string      // 持仓方向: BOTH, LONG, SHORT
  positionAmt?: string       // 持仓数量
  unrealizedProfit?: string  // 未实现盈亏
  // V3 版本字段
  isolatedMargin?: string   // 逐仓保证金
  notional?: string          // 名义价值
  isolatedWallet?: string   // 逐仓钱包余额
  initialMargin?: string    // 持仓所需起始保证金
  maintMargin?: string      // 维持保证金
  updateTime?: number       // 更新时间
}

/**
 * 期货账户信息
 *
 * 对应 V3 API: GET /fapi/v3/account
 * 注意：V3 API 不返回 feeTier, feeBurn, canTrade/canDeposit/canWithdraw, multiAssetsMargin 等字段
 * 使用 camelCase 与 API 响应保持一致
 */
export interface FuturesAccountInfo {
  // 账户余额（汇总）- V3 API 返回
  totalInitialMargin?: string
  totalMaintMargin?: string
  totalWalletBalance?: string
  totalUnrealizedProfit?: string
  totalMarginBalance?: string
  // 持仓相关保证金
  totalPositionInitialMargin?: string
  totalOpenOrderInitialMargin?: string
  // 全仓相关
  totalCrossWalletBalance?: string
  totalCrossUnrealizedProfit?: string
  // 可用余额
  availableBalance?: string
  maxWithdrawAmount?: string
  // 详细列表
  assets: FuturesAsset[]
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
 *
 * 后端返回格式：
 * {
 *   type: "futures_account" | "spot_account",
 *   content: SpotAccountInfo | FuturesAccountInfo,
 *   updateTime: number
 * }
 */
export interface AccountResponse {
  /** 账户类型标识 */
  type: string
  /** 账户信息内容 */
  content: SpotAccountInfo | FuturesAccountInfo
  /** 更新时间 */
  updateTime?: number
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
 *
 * 注意: /fapi/v3/account 返回的字段有限，部分字段可能为 '-'
 * 完整数据需调用 /fapi/v3/positionRisk
 */
export interface PositionItem {
  /** 交易对 */
  symbol: string
  /** 持仓方向: long(多头), short(空头), both(双向/单向持仓) */
  side: 'long' | 'short' | 'both'
  /** 持仓数量 */
  amount: string
  /** 开仓价格 (V3 API 可能不返回) */
  entryPrice: string
  /** 标记价格 (V3 API 可能不返回) */
  markPrice: string
  /** 未实现盈亏 */
  unrealizedPnl: string
  /** 持仓保证金 */
  margin: string
  /** 强平价格 (V3 API 可能不返回) */
  liquidationPrice?: string
  /** 名义价值 */
  notional?: string
  /** 杠杆倍数 (V3 API 可能不返回) */
  leverage?: string
  /** 是否逐仓 (V3 API 可能不返回) */
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

// ==================== 常量定义 ====================

/**
 * 账户类型选项
 */
export const ACCOUNT_TYPE_OPTIONS: { label: string; value: 'spot' | 'futures' }[] = [
  { label: '现货账户', value: 'spot' },
  { label: 'U本位合约', value: 'futures' },
]
