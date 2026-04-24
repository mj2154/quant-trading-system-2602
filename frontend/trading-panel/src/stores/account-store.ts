/**
 * 账户信息状态管理 Store
 *
 * 管理账户信息查询和实时更新
 *
 * 架构设计:
 * - UI显示模型(SpotAccountDisplay/FuturesAccountDisplay)与API原始数据分离
 * - 通过Converter将API数据转换为显示模型
 * - WS增量更新通过Converter应用到显示模型
 *
 * 使用 DataService 统一管理 WebSocket 连接
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dataService } from '../services/data-service/DataService'
import type {
  AccountUpdate,
  SpotAccountUpdate,
  SpotBalanceUpdateEvent,
  SpotExecutionReportEvent,
  FuturesAccountUpdate,
  FuturesAccountConfigUpdate,
  FuturesOrderTradeUpdate,
  FuturesTradeLiteEvent,
  FuturesMarginCall,
  FuturesAlgoUpdate,
  FuturesStrategyUpdate,
  FuturesGridUpdate,
  FuturesConditionalOrderTriggerReject,
} from '../types/api'
import type {
  SpotAccountDisplay,
  FuturesAccountDisplay,
  SpotBalanceDisplay,
  FuturesPositionDisplay,
} from '../types/display/account-display'
import {
  convertSpotAccountToDisplay,
  convertFuturesAccountToDisplay,
  applySpotOutboundUpdate,
  applySpotBalanceUpdate,
  applyFuturesAccountUpdate,
} from '../converters/account-converter'

// ==================== 类型别名 ====================

/** @deprecated 使用 SpotAccountDisplay 替代 */
type SpotAccountInfo = SpotAccountDisplay
/** @deprecated 使用 FuturesAccountDisplay 替代 */
type FuturesAccountInfo = FuturesAccountDisplay

// ==================== Store 定义 ====================

export const useAccountStore = defineStore('account', () => {
  // ==================== 显示模型状态 ====================

  /** 现货账户显示模型 */
  const spotDisplay = ref<SpotAccountDisplay | null>(null)
  const spotLoading = ref(false)
  const spotError = ref<string | null>(null)

  /** 期货账户显示模型 */
  const futuresDisplay = ref<FuturesAccountDisplay | null>(null)
  const futuresLoading = ref(false)
  const futuresError = ref<string | null>(null)

  /** 期货杠杆率映射表 (symbol -> leverage) */
  const leverageMap = ref<Record<string, number>>({})

  /** WebSocket连接状态 */
  const wsConnected = ref(false)

  /** 账户订阅状态 */
  let spotUnsubscribe: (() => void) | null = null
  let futuresUnsubscribe: (() => void) | null = null

  // ==================== 计算属性 ====================

  /**
   * 现货账户概览
   *
   * @deprecated 直接使用 spotDisplay
   */
  const spotOverview = computed(() => {
    if (!spotDisplay.value) return null

    return {
      accountType: 'spot' as const,
      totalAsset: spotDisplay.value.totalAsset,
      availableBalance: spotDisplay.value.availableBalance,
      positionCount: 0, // 现货无持仓概念
      updateTime: spotDisplay.value.updateTime
        ? new Date(spotDisplay.value.updateTime).toLocaleString()
        : '-',
    }
  })

  /**
   * 期货账户概览
   *
   * @deprecated 直接使用 futuresDisplay
   */
  const futuresOverview = computed(() => {
    if (!futuresDisplay.value) return null

    const positions = futuresDisplay.value.positions || []
    const positionCount = positions.filter(
      p => parseFloat(p.positionAmt || '0') !== 0
    ).length

    return {
      accountType: 'futures' as const,
      totalAsset: futuresDisplay.value.totalMarginBalance,
      availableBalance: futuresDisplay.value.availableBalance,
      positionCount,
      updateTime: futuresDisplay.value.updateTime
        ? new Date(futuresDisplay.value.updateTime).toLocaleString()
        : '-',
    }
  })

  /**
   * 期货持仓列表
   *
   * @deprecated 直接使用 futuresDisplay.positions
   */
  const futuresPositions = computed((): FuturesPositionDisplay[] => {
    if (!futuresDisplay.value?.positions) return []

    return futuresDisplay.value.positions.filter(
      p => parseFloat(p.positionAmt || '0') !== 0
    )
  })

  /**
   * 期货资产列表
   *
   * @deprecated 直接使用 futuresDisplay.assets
   */
  const futuresAssets = computed(() => {
    return futuresDisplay.value?.assets || []
  })

  /**
   * 现货余额列表
   *
   * @deprecated 直接使用 spotDisplay.balances
   */
  const spotBalances = computed((): SpotBalanceDisplay[] => {
    if (!spotDisplay.value?.balances) return []
    return spotDisplay.value.balances
  })

  // ==================== 账户 Actions ====================

  /**
   * 获取现货账户信息
   *
   * @deprecated 使用 fetchAndConvertSpotAccount 替代
   */
  async function fetchSpotAccount(): Promise<SpotAccountDisplay | null> {
    spotLoading.value = true
    spotError.value = null
    wsConnected.value = false

    try {
      // 使用 DataService 获取现货账户信息
      const apiData = await dataService.getSpotAccount()

      // 转换为显示模型
      spotDisplay.value = convertSpotAccountToDisplay(apiData)
      wsConnected.value = true

      return spotDisplay.value
    } catch (error) {
      spotError.value = error instanceof Error
        ? error.message
        : '获取现货账户信息失败'
      console.warn('fetchSpotAccount error:', error)
      return null
    } finally {
      spotLoading.value = false
    }
  }

  /**
   * 获取期货账户信息
   *
   * @deprecated 使用 fetchAndConvertFuturesAccount 替代
   */
  async function fetchFuturesAccount(): Promise<FuturesAccountDisplay | null> {
    futuresLoading.value = true
    futuresError.value = null
    wsConnected.value = false

    try {
      // 使用 DataService 获取期货账户信息
      const apiData = await dataService.getFuturesAccount()

      // 转换为显示模型
      futuresDisplay.value = convertFuturesAccountToDisplay(apiData)
      wsConnected.value = true

      // 注意: GET API 不返回 leverage 字段，leverageMap 只能通过 WS ACCOUNT_CONFIG_UPDATE 事件维护
      // 不再从 GET API 初始化 leverageMap，避免覆盖 WS 已推送的值

      return futuresDisplay.value
    } catch (error) {
      futuresError.value = error instanceof Error
        ? error.message
        : '获取期货账户信息失败'
      console.warn('fetchFuturesAccount error:', error)
      return null
    } finally {
      futuresLoading.value = false
    }
  }

  /**
   * 刷新账户信息
   *
   * 同时获取现货和期货账户数据并转换为显示模型
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

  // ==================== WS订阅处理 ====================

  /**
   * 处理现货账户增量更新
   */
  function handleSpotAccountUpdate(update: AccountUpdate): void {
    if (!spotDisplay.value) return

    if (isSpotOutboundAccountPosition(update)) {
      // outboundAccountPosition: 账户余额变化，包含所有余额
      spotDisplay.value = applySpotOutboundUpdate(spotDisplay.value, update)
    } else if (isSpotBalanceUpdateEvent(update)) {
      // balanceUpdate: 充值/提现/转账，包含单个资产变化
      spotDisplay.value = applySpotBalanceUpdate(spotDisplay.value, update)
    } else if (isSpotExecutionReportEvent(update)) {
      // executionReport: 订单执行报告(当前不处理余额，只记录日志)
      console.debug('[AccountStore] executionReport:', update)
    }
  }

  /**
   * 判断是否为 outboundAccountPosition 事件
   */
  function isSpotOutboundAccountPosition(
    update: AccountUpdate
  ): update is SpotAccountUpdate {
    return (update as SpotAccountUpdate).e === 'outboundAccountPosition'
  }

  /**
   * 判断是否为 balanceUpdate 事件
   */
  function isSpotBalanceUpdateEvent(
    update: AccountUpdate
  ): update is SpotBalanceUpdateEvent {
    return (update as SpotBalanceUpdateEvent).e === 'balanceUpdate'
  }

  /**
   * 判断是否为 executionReport 事件
   */
  function isSpotExecutionReportEvent(
    update: AccountUpdate
  ): update is SpotExecutionReportEvent {
    return (update as SpotExecutionReportEvent).e === 'executionReport'
  }

  /**
   * 判断是否为期货账户更新事件
   */
  function isFuturesAccountUpdate(
    update: AccountUpdate
  ): update is FuturesAccountUpdate {
    return (update as FuturesAccountUpdate).e === 'ACCOUNT_UPDATE'
  }

  /**
   * 判断是否为期货账户配置更新事件
   */
  function isFuturesAccountConfigUpdate(
    update: AccountUpdate
  ): update is FuturesAccountConfigUpdate {
    return (update as FuturesAccountConfigUpdate).e === 'ACCOUNT_CONFIG_UPDATE'
  }

  /**
   * 判断是否为期货订单成交更新事件
   */
  function isFuturesOrderTradeUpdate(
    update: AccountUpdate
  ): update is FuturesOrderTradeUpdate {
    return (update as FuturesOrderTradeUpdate).e === 'ORDER_TRADE_UPDATE'
  }

  /**
   * 判断是否为期货简化交易事件
   */
  function isFuturesTradeLiteEvent(
    update: AccountUpdate
  ): update is FuturesTradeLiteEvent {
    return (update as FuturesTradeLiteEvent).e === 'TRADE_LITE'
  }

  /**
   * 判断是否为期货保证金追缴事件
   *
   * 高优先级事件，涉及强平风险，需要告警通知
   */
  function isFuturesMarginCall(
    update: AccountUpdate
  ): update is FuturesMarginCall {
    return (update as FuturesMarginCall).e === 'MARGIN_CALL'
  }

  /**
   * 判断是否为期货条件单更新事件
   */
  function isFuturesAlgoUpdate(
    update: AccountUpdate
  ): update is FuturesAlgoUpdate {
    return (update as FuturesAlgoUpdate).e === 'ALGO_UPDATE'
  }

  /**
   * 判断是否为期货策略更新事件
   */
  function isFuturesStrategyUpdate(
    update: AccountUpdate
  ): update is FuturesStrategyUpdate {
    return (update as FuturesStrategyUpdate).e === 'STRATEGY_UPDATE'
  }

  /**
   * 判断是否为期货网格更新事件
   */
  function isFuturesGridUpdate(
    update: AccountUpdate
  ): update is FuturesGridUpdate {
    return (update as FuturesGridUpdate).e === 'GRID_UPDATE'
  }

  /**
   * 判断是否为期货条件单触发拒绝事件
   */
  function isFuturesConditionalOrderTriggerReject(
    update: AccountUpdate
  ): update is FuturesConditionalOrderTriggerReject {
    return (update as FuturesConditionalOrderTriggerReject).e === 'CONDITIONAL_ORDER_TRIGGER_REJECT'
  }

  /**
   * 处理期货账户增量更新
   */
  function handleFuturesAccountUpdate(update: FuturesAccountUpdate): void {
    if (!futuresDisplay.value) {
      console.warn('[AccountStore] 期货账户未初始化，跳过更新')
      return
    }

    futuresDisplay.value = applyFuturesAccountUpdate(
      futuresDisplay.value,
      update,
      leverageMap.value
    )

    console.debug(
      '[AccountStore] 期货账户更新完成',
      'totalWalletBalance:',
      futuresDisplay.value.totalWalletBalance
    )
  }

  /**
   * 处理期货账户配置更新 (ACCOUNT_CONFIG_UPDATE事件)
   *
   * 包含杠杆率变更和多资产模式变更
   */
  function handleFuturesAccountConfigUpdate(
    update: FuturesAccountConfigUpdate
  ): void {
    if (!futuresDisplay.value) {
      console.warn('[AccountStore] 期货账户未初始化，跳过配置更新')
      return
    }

    // 处理杠杆率变更
    if (update.ac) {
      leverageMap.value = {
        ...leverageMap.value,
        [update.ac.s]: update.ac.l,
      }

      // 更新对应持仓的杠杆率
      const positionIndex = futuresDisplay.value.positions.findIndex(
        p => p.symbol === update.ac!.s
      )
      if (positionIndex >= 0) {
        const newPositions = [...futuresDisplay.value.positions]
        newPositions[positionIndex] = {
          ...newPositions[positionIndex],
          leverage: update.ac.l,
        }
        futuresDisplay.value = {
          ...futuresDisplay.value,
          positions: newPositions,
        }
      }

      console.debug(
        '[AccountStore] 杠杆率更新',
        update.ac.s,
        '->',
        update.ac.l
      )
    }

    // 处理多资产模式变更
    if (update.ai !== undefined) {
      futuresDisplay.value = {
        ...futuresDisplay.value,
        multiAssetsMargin: update.ai.j,
      }
      console.debug(
        '[AccountStore] 多资产模式更新',
        '->',
        update.ai.j
      )
    }
  }

  /**
   * 处理期货订单成交更新 (ORDER_TRADE_UPDATE事件)
   */
  function handleFuturesOrderTradeUpdate(update: FuturesOrderTradeUpdate): void {
    // 订单状态更新记录日志
    console.debug('[AccountStore] ORDER_TRADE_UPDATE:', update)
  }

  /**
   * 处理期货简化交易事件 (TRADE_LITE事件)
   */
  function handleFuturesTradeLiteEvent(update: FuturesTradeLiteEvent): void {
    // 简化交易事件记录日志
    console.debug('[AccountStore] TRADE_LITE:', update)
  }

  /**
   * 处理期货保证金追缴事件 (MARGIN_CALL事件)
   *
   * 高优先级：涉及强平风险，需要告警通知
   *
   * MARGIN_CALL事件推送的字段:
   * - mp: 标记价格 (markPrice)
   * - mm: 维持保证金要求 (maintMargin)
   *
   * 注意: MARGIN_CALL只在仓位风险时才推送，因此更新时直接覆盖
   */
  function handleFuturesMarginCall(update: FuturesMarginCall): void {
    if (!futuresDisplay.value) {
      console.warn('[AccountStore] 期货账户未初始化，跳过保证金追缴更新')
      return
    }

    const positions = update.p || []
    const warningMsg = `[AccountStore] 保证金追缴警告！跨账户钱包余额: ${update.cw}`

    console.warn(warningMsg, '追缴持仓:', positions)

    // 更新匹配持仓的标记价格和维持保证金
    const newPositions = futuresDisplay.value.positions.map(position => {
      const marginPosition = positions.find(p => p.s === position.symbol)
      if (marginPosition) {
        return {
          ...position,
          markPrice: marginPosition.mp,
          maintMargin: marginPosition.mm,
        }
      }
      return position
    })

    futuresDisplay.value = {
      ...futuresDisplay.value,
      positions: newPositions,
    }

    // TODO: 触发浏览器通知或UI告警
    // 建议：使用 Notification API 或调用告警组件
  }

  /**
   * 处理期货条件单更新事件 (ALGO_UPDATE事件)
   */
  function handleFuturesAlgoUpdate(update: FuturesAlgoUpdate): void {
    console.debug('[AccountStore] ALGO_UPDATE:', update)
  }

  /**
   * 处理期货策略更新事件 (STRATEGY_UPDATE事件)
   */
  function handleFuturesStrategyUpdate(update: FuturesStrategyUpdate): void {
    console.debug('[AccountStore] STRATEGY_UPDATE:', update)
  }

  /**
   * 处理期货网格更新事件 (GRID_UPDATE事件)
   */
  function handleFuturesGridUpdate(update: FuturesGridUpdate): void {
    console.debug('[AccountStore] GRID_UPDATE:', update)
  }

  /**
   * 处理期货条件单触发拒绝事件 (CONDITIONAL_ORDER_TRIGGER_REJECT事件)
   */
  function handleFuturesConditionalOrderTriggerReject(
    update: FuturesConditionalOrderTriggerReject
  ): void {
    console.debug('[AccountStore] CONDITIONAL_ORDER_TRIGGER_REJECT:', update)
  }

  // ==================== 生命周期 ====================

  /**
   * 初始化 Store - 连接 DataService 并订阅账户增量
   *
   * 先获取完整数据并转换为显示模型，再订阅WS增量更新
   */
  async function initialize(): Promise<void> {
    // 1. 先获取完整账户数据
    await refreshAccounts()

    // 2. 订阅现货账户增量更新
    spotUnsubscribe = dataService.subscribeAccount('SPOT', (update) => {
      handleSpotAccountUpdate(update)
    })

    // 3. 订阅期货账户增量更新
    futuresUnsubscribe = dataService.subscribeAccount('FUTURES', (update) => {
      if (isFuturesAccountUpdate(update)) {
        handleFuturesAccountUpdate(update)
      } else if (isFuturesAccountConfigUpdate(update)) {
        handleFuturesAccountConfigUpdate(update)
      } else if (isFuturesOrderTradeUpdate(update)) {
        handleFuturesOrderTradeUpdate(update)
      } else if (isFuturesTradeLiteEvent(update)) {
        handleFuturesTradeLiteEvent(update)
      } else if (isFuturesMarginCall(update)) {
        handleFuturesMarginCall(update)
      } else if (isFuturesAlgoUpdate(update)) {
        handleFuturesAlgoUpdate(update)
      } else if (isFuturesStrategyUpdate(update)) {
        handleFuturesStrategyUpdate(update)
      } else if (isFuturesGridUpdate(update)) {
        handleFuturesGridUpdate(update)
      } else if (isFuturesConditionalOrderTriggerReject(update)) {
        handleFuturesConditionalOrderTriggerReject(update)
      }
    })
  }

  /**
   * 重置 Store
   */
  function reset() {
    // 清理现货账户订阅
    if (spotUnsubscribe) {
      spotUnsubscribe()
      spotUnsubscribe = null
    }

    // 清理期货账户订阅
    if (futuresUnsubscribe) {
      futuresUnsubscribe()
      futuresUnsubscribe = null
    }

    spotDisplay.value = null
    spotLoading.value = false
    spotError.value = null
    futuresDisplay.value = null
    futuresLoading.value = false
    futuresError.value = null
    leverageMap.value = {}
    wsConnected.value = false
  }

  return {
    // ==================== 状态 (显示模型) ====================
    /** @deprecated 使用 spotDisplay 替代 */
    spotAccount: spotDisplay,
    spotLoading,
    spotError,
    /** @deprecated 使用 futuresDisplay 替代 */
    futuresAccount: futuresDisplay,
    futuresLoading,
    futuresError,
    wsConnected,

    // ==================== 显示模型 (新) ====================
    spotDisplay,
    futuresDisplay,

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
