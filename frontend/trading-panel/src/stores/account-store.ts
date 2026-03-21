/**
 * 账户信息状态管理 Store
 *
 * 管理账户信息查询和实时更新
 *
 * 使用 DataService 统一管理 WebSocket 连接
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dataService } from '../services/data-service/DataService'
import type {
  SpotAccountDetail,
  SpotAccountData,
  FuturesAccountDetail,
  FuturesAccountData,
  FuturesAccountAsset,
  FuturesAccountPosition,
} from '../types/api'

// 类型别名，保持向后兼容
type SpotAccountInfo = SpotAccountDetail
type FuturesAccountInfo = FuturesAccountDetail

// 前端展示类型（Store 内部使用）
interface AccountOverview {
  accountType: 'spot' | 'futures'
  totalAsset: string
  availableBalance: string
  positionCount: number
  updateTime: string
}

interface PositionItem {
  symbol: string
  side: 'long' | 'short' | 'both'
  amount: string
  entryPrice: string
  markPrice: string
  unrealizedPnl: string
  margin: string
  liquidationPrice?: string
  notional?: string
}

interface BalanceItem {
  asset: string
  free: string
  locked: string
  total: string
}

// ==================== Store 定义 ====================

export const useAccountStore = defineStore('account', () => {
  // ==================== 状态 ====================

  // 现货账户信息
  const spotAccount = ref<SpotAccountInfo | null>(null)
  const spotLoading = ref(false)
  const spotError = ref<string | null>(null)

  // 期货账户信息
  const futuresAccount = ref<FuturesAccountInfo | null>(null)
  const futuresLoading = ref(false)
  const futuresError = ref<string | null>(null)

  // DataService 连接状态
  const wsConnected = ref(false)

  // ==================== 计算属性 ====================

  /**
   * 现货账户概览
   *
   * 注意：totalUSDT 计算为简化实现，仅统计 USDT 余额。
   * 完整实现需要获取各币种对 USDT 的实时价格进行换算。
   */
  const spotOverview = computed((): AccountOverview | null => {
    if (!spotAccount.value) return null

    const balances = spotAccount.value.balances || []
    // 计算总资产（简化计算：仅统计 USDT 余额）
    // 完整实现需要获取各币种实时价格进行换算
    const usdtBalance = balances.find(b => b.asset === 'USDT')
    const totalUSDT = (parseFloat(usdtBalance?.free || '0') + parseFloat(usdtBalance?.locked || '0'))

    return {
      accountType: 'spot',
      totalAsset: totalUSDT.toFixed(2),
      availableBalance: usdtBalance?.free || '0',
      positionCount: 0,
      updateTime: spotAccount.value.updateTime
        ? new Date(spotAccount.value.updateTime).toLocaleString()
        : '-',
    }
  })

  /**
   * 期货账户概览
   */
  const futuresOverview = computed((): AccountOverview | null => {
    if (!futuresAccount.value) return null

    const positions = futuresAccount.value.positions || []
    const positionCount = positions.filter(p => parseFloat(p.positionAmt || '0') !== 0).length

    return {
      accountType: 'futures',
      totalAsset: futuresAccount.value.totalWalletBalance || '0',
      availableBalance: futuresAccount.value.availableBalance || futuresAccount.value.totalWalletBalance || '0',
      positionCount,
      updateTime: futuresAccount.value.updateTime
        ? new Date(futuresAccount.value.updateTime).toLocaleString()
        : '-',
    }
  })

  /**
   * 期货持仓列表
   *
   * 注意: /fapi/v3/account 返回的持仓数据是简化版本
   * 仅返回: symbol, positionSide, positionAmt, unrealizedProfit,
   *        isolatedMargin, notional, isolatedWallet, initialMargin, maintMargin, updateTime
   * 不返回: entryPrice, markPrice, liquidationPrice, leverage (这些需要 /fapi/v3/positionRisk)
   */
  const futuresPositions = computed((): PositionItem[] => {
    if (!futuresAccount.value?.positions) return []

    return futuresAccount.value.positions
      .filter(p => parseFloat(p.positionAmt || '0') !== 0)
      .map(p => ({
        symbol: p.symbol,
        // 持仓方向: BOTH(单向持仓), LONG(多头), SHORT(空头)
        side: (p.positionSide?.toLowerCase() || 'both') as 'long' | 'short' | 'both',
        // 持仓数量
        amount: p.positionAmt || '0',
        // 开仓价格 (V3 API 不返回，显示为 -)
        entryPrice: '-',
        // 标记价格 (V3 API 不返回，显示为 -)
        markPrice: '-',
        // 未实现盈亏
        unrealizedPnl: p.unrealizedProfit || '0',
        // 持仓保证金: 逐仓用 isolatedMargin，全仓用 initialMargin
        margin: p.isolatedMargin || p.initialMargin || '0',
        // 强平价格 (V3 API 不返回，显示为 -)
        liquidationPrice: '-',
        // 名义价值
        notional: p.notional || '0',
      }))
  })

  /**
   * 期货资产列表
   */
  const futuresAssets = computed(() => {
    if (!futuresAccount.value?.assets) return []
    return futuresAccount.value.assets
  })

  /**
   * 现货余额列表
   */
  const spotBalances = computed((): BalanceItem[] => {
    if (!spotAccount.value?.balances) return []

    return spotAccount.value.balances
      .map(b => {
        const free = parseFloat(b.free || '0')
        const locked = parseFloat(b.locked || '0')
        return {
          asset: b.asset,
          free: b.free || '0',
          locked: b.locked || '0',
          total: (free + locked).toString(),
        }
      })
      .filter(b => parseFloat(b.total) > 0)
      .sort((a, b) => parseFloat(b.total) - parseFloat(a.total))
  })

  // ==================== 账户 Actions ====================

  /**
   * 获取现货账户信息
   */
  async function fetchSpotAccount(): Promise<SpotAccountInfo | null> {
    spotLoading.value = true
    spotError.value = null
    wsConnected.value = false

    try {
      // 使用 DataService 获取现货账户信息
      const account = await dataService.getSpotAccount()
      spotAccount.value = account
      wsConnected.value = true
      return account
    } catch (error) {
      spotError.value = error instanceof Error ? error.message : '获取现货账户信息失败'
      console.warn('fetchSpotAccount error:', error)
      return null
    } finally {
      spotLoading.value = false
    }
  }

  /**
   * 获取期货账户信息
   */
  async function fetchFuturesAccount(): Promise<FuturesAccountInfo | null> {
    futuresLoading.value = true
    futuresError.value = null
    wsConnected.value = false

    try {
      // 使用 DataService 获取期货账户信息
      const account = await dataService.getFuturesAccount()
      futuresAccount.value = account
      wsConnected.value = true
      return account
    } catch (error) {
      futuresError.value = error instanceof Error ? error.message : '获取期货账户信息失败'
      console.warn('fetchFuturesAccount error:', error)
      return null
    } finally {
      futuresLoading.value = false
    }
  }

  /**
   * 刷新账户信息
   */
  async function refreshAccounts(): Promise<void> {
    await Promise.all([
      fetchSpotAccount(),
      fetchFuturesAccount(),
    ])
  }

  /**
   * 清除错误
   */
  function clearError() {
    spotError.value = null
    futuresError.value = null
  }

  // ==================== 初始化 ====================

  /**
   * 初始化 Store - 连接 DataService
   */
  function initialize() {
    console.debug('[AccountStore] 初始化 Store')
    // DataService 会自动连接，不需要手动调用
    // 首次调用 fetchSpotAccount 或 fetchFuturesAccount 时会自动连接
  }

  /**
   * 重置 Store
   */
  function reset() {
    spotAccount.value = null
    spotLoading.value = false
    spotError.value = null
    futuresAccount.value = null
    futuresLoading.value = false
    futuresError.value = null
    wsConnected.value = false
  }

  return {
    // ==================== 状态 ====================
    spotAccount,
    spotLoading,
    spotError,
    futuresAccount,
    futuresLoading,
    futuresError,
    wsConnected,

    // ==================== 计算属性 ====================
    spotOverview,
    futuresOverview,
    futuresPositions,
    futuresAssets,
    spotBalances,

    // ==================== Actions ====================
    fetchSpotAccount,
    fetchFuturesAccount,
    refreshAccounts,
    clearError,

    // ==================== 生命周期 ====================
    initialize,
    reset,
  }
})
