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
  AccountUpdate,
  SpotAccountUpdate,
  SpotBalanceUpdateEvent,
  SpotExecutionReportEvent,
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

  // 账户订阅状态
  let spotUnsubscribe: (() => void) | null = null

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

  // ==================== 账户订阅 ====================

  /**
   * 处理现货账户增量更新
   *
   * @param update - 账户更新消息
   */
  function handleSpotAccountUpdate(update: AccountUpdate): void {
    // 判断事件类型并分别处理
    if (isSpotAccountUpdate(update)) {
      handleOutboundAccountPosition(update)
    } else if (isSpotBalanceUpdateEvent(update)) {
      handleBalanceUpdate(update)
    } else if (isSpotExecutionReportEvent(update)) {
      handleExecutionReport(update)
    }
  }

  /**
   * 判断是否为 outboundAccountPosition 事件
   */
  function isSpotAccountUpdate(update: AccountUpdate): update is SpotAccountUpdate {
    return (update as SpotAccountUpdate).e === 'outboundAccountPosition'
  }

  /**
   * 判断是否为 balanceUpdate 事件
   */
  function isSpotBalanceUpdateEvent(update: AccountUpdate): update is SpotBalanceUpdateEvent {
    return (update as SpotBalanceUpdateEvent).e === 'balanceUpdate'
  }

  /**
   * 判断是否为 executionReport 事件
   */
  function isSpotExecutionReportEvent(update: AccountUpdate): update is SpotExecutionReportEvent {
    return (update as SpotExecutionReportEvent).e === 'executionReport'
  }

  /**
   * 处理账户余额变化事件 (outboundAccountPosition)
   *
   * 币安推送: 当账户余额发生变化时推送，包含所有余额
   */
  function handleOutboundAccountPosition(update: SpotAccountUpdate): void {
    if (!spotAccount.value || !update.B) return

    // 更新余额：遍历更新列表，直接替换对应资产的余额
    for (const balanceUpdate of update.B) {
      const existingBalance = spotAccount.value.balances?.find(
        b => b.asset === balanceUpdate.a
      )

      if (existingBalance) {
        // 更新现有资产余额
        existingBalance.free = balanceUpdate.f
        existingBalance.locked = balanceUpdate.l
      } else {
        // 添加新资产余额
        if (spotAccount.value.balances) {
          spotAccount.value.balances.push({
            asset: balanceUpdate.a,
            free: balanceUpdate.f,
            locked: balanceUpdate.l,
          })
        }
      }
    }

    // 更新账户时间戳
    spotAccount.value.updateTime = update.u

    console.debug('[AccountStore] 现货账户余额更新:', update.B)
  }

  /**
   * 处理余额变化事件 (balanceUpdate)
   *
   * 币安推送: 充值/提现/转账时推送，包含单个资产变化
   */
  function handleBalanceUpdate(update: SpotBalanceUpdateEvent): void {
    if (!spotAccount.value) return

    // 查找现有余额
    const existingBalance = spotAccount.value.balances?.find(
      b => b.asset === update.a
    )

    if (existingBalance) {
      // 应用增量变化
      const delta = parseFloat(update.d)
      const currentFree = parseFloat(existingBalance.free)
      existingBalance.free = (currentFree + delta).toString()
    } else {
      // 新资产，创建余额记录
      if (spotAccount.value.balances) {
        spotAccount.value.balances.push({
          asset: update.a,
          free: update.d,
          locked: '0',
        })
      }
    }

    console.debug('[AccountStore] 现货余额变化:', update.a, update.d)
  }

  /**
   * 处理订单执行报告事件 (executionReport)
   *
   * 币安推送: 订单状态变化时推送（新建/成交/取消等）
   * 注意：此事件不直接更新余额，余额通过 outboundAccountPosition 更新
   */
  function handleExecutionReport(update: SpotExecutionReportEvent): void {
    console.debug('[AccountStore] 现货订单执行报告:', {
      symbol: update.s,
      orderId: update.i,
      side: update.S,
      type: update.o,
      status: update.X,
      executedQty: update.q,
    })
  }

  // ==================== 初始化 ====================

  /**
   * 初始化 Store - 连接 DataService 并订阅账户增量
   */
  function initialize() {
    console.debug('[AccountStore] 初始化 Store')

    // 订阅现货账户增量更新
    spotUnsubscribe = dataService.subscribeAccount('SPOT', (update) => {
      handleSpotAccountUpdate(update)
    })

    console.debug('[AccountStore] 已订阅现货账户增量更新')
  }

  /**
   * 重置 Store
   */
  function reset() {
    // 清理订阅
    if (spotUnsubscribe) {
      spotUnsubscribe()
      spotUnsubscribe = null
    }

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
