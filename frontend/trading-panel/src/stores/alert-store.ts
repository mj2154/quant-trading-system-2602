/**
 * 告警管理状态管理 Store
 *
 * 管理告警配置列表、告警信号历史、CRUD 操作
 * 使用 DataService 获取数据，保持单一 WebSocket 连接
 *
 * 使用 WebSocket 协议 (protocolVersion 2.0) 与后端通信
 * 使用 camelCase 与协议保持一致
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dataService } from '../services/data-service/DataService'
import type {
  SignalRecord,
  AlertConfig,
  CreateAlertConfigRequest,
  UpdateAlertConfigRequest,
} from '../types/api'
import type { SignalRecordQueryParams } from '../types/api/signal'

// Re-export types for other components
export type { SignalRecord }
export type { AlertConfig }
export type { CreateAlertConfigRequest }
export type { UpdateAlertConfigRequest }

// ==================== 常量定义 ====================

/**
 * 触发类型选项
 */
export const ALERT_TRIGGER_TYPE_OPTIONS = [
  { label: '仅一次 (once_only)', value: 'once_only' },
  { label: '每根K线 (each_kline)', value: 'each_kline' },
  { label: '每根K线收盘 (each_kline_close)', value: 'each_kline_close' },
  { label: '每分钟 (each_minute)', value: 'each_minute' },
]

/**
 * 策略类型选项（直接使用类名）
 * 用于下拉选择框
 */
export const ALERT_STRATEGY_TYPE_OPTIONS = [
  { label: 'MACD共振策略V5', value: 'MACDResonanceStrategyV5' },
  { label: 'MACD共振策略V6', value: 'MACDResonanceStrategyV6' },
  { label: 'MACD做空策略', value: 'MACDResonanceShortStrategy' },
  { label: 'Alpha01策略', value: 'Alpha01Strategy' },
]

/**
 * MACD 默认参数（前端表单使用的简写名称）
 * 注意：发送到后端时会自动转换为完整参数名
 * 后端要求的参数名: macd1_fastperiod, macd1_slowperiod, macd1_signalperiod 等
 */

/**
 * 将 snake_case 参数名转换为人类友好的显示格式
 * 例如: macd1_fastperiod -> "Macd1 Fastperiod"
 *       fast_period -> "Fast Period"
 *       macd2_signalperiod -> "Macd2 Signalperiod"
 */
export function formatParamName(name: string): string {
  return name
    .replace(/_/g, ' ')  // 下划线替换为空格
    .replace(/(\d+)/g, '$1')  // 数字前后不加空格，保持连续
    .replace(/\s+/g, ' ')  // 多个空格合并为一个
    .trim()
    .replace(/^\w/, c => c.toUpperCase())  // 首字母大写
}

export const DEFAULT_PARAMS = {
  macd1_fastperiod: 12,
  macd1_slowperiod: 26,
  macd1_signalperiod: 9,
  macd2_fastperiod: 5,
  macd2_slowperiod: 10,
  macd2_signalperiod: 4,
}

// ==================== Store 定义 ====================

export const useAlertStore = defineStore('alert', () => {
  // ==================== 状态 ====================

  // 告警配置列表
  const alerts = ref<AlertConfig[]>([])
  const alertsLoading = ref(false)
  const alertsError = ref<string | null>(null)

  // 当前选中的告警
  const currentAlert = ref<AlertConfig | null>(null)

  // 告警信号历史列表
  const alertSignals = ref<SignalRecord[]>([])
  const alertSignalsLoading = ref(false)
  const alertSignalsError = ref<string | null>(null)

  // 信号查询参数
  const alertSignalQueryParams = ref<SignalRecordQueryParams>({
    page: 1,
    pageSize: 20,
    orderBy: 'computedAt',
    orderDir: 'desc',
  })

  // DataService 连接状态
  const wsConnected = ref(false)

  // 实时告警信号列表
  const realtimeAlertSignals = ref<SignalRecord[]>([])
  const maxRealtimeAlertSignals = 50 // 最多保留50条实时信号

  // 实时信号订阅取消函数
  let signalUnsubscribe: (() => void) | null = null

  // 告警信号到达回调 - 用于触发弹窗和声音
  const onSignalCallback = ref<((signal: SignalRecord) => void) | null>(null)

  // ==================== 计算属性 ====================

  const enabledAlerts = computed(() =>
    alerts.value.filter(a => a.isEnabled)
  )

  const realtimeAlertSignalsCount = computed(() => realtimeAlertSignals.value.length)

  // ==================== 告警配置 Actions ====================

  /**
   * 获取告警配置列表（使用 DataService）
   */
  async function fetchAlerts() {
    alertsLoading.value = true
    alertsError.value = null
    try {
      // DataService 已完成所有数据转换（snake_case -> camelCase + 默认值填充）
      alerts.value = await dataService.listAlertConfigs(1, 100)

      // 告警列表加载完成后，订阅这些告警的信号事件
      subscribeToAlertSignalEvents()
    } catch (error) {
      alertsError.value = error instanceof Error ? error.message : '获取告警列表失败'
      console.error('fetchAlerts error:', error)
    } finally {
      alertsLoading.value = false
    }
  }

  /**
   * 获取单个告警配置（使用 DataService）
   */
  async function fetchAlert(id: string): Promise<AlertConfig | null> {
    alertsLoading.value = true
    alertsError.value = null
    try {
      // DataService 已完成所有数据转换
      currentAlert.value = await dataService.getAlert(id)
      return currentAlert.value
    } catch (error) {
      alertsError.value = error instanceof Error ? error.message : '获取告警详情失败'
      console.error('fetchAlert error:', error)
      return null
    } finally {
      alertsLoading.value = false
    }
  }

  /**
   * 创建告警配置（使用 DataService）
   */
  async function createAlert(config: {
    name: string
    description?: string
    strategyType: string
    symbol: string
    interval: string
    triggerType?: string
    params?: Record<string, number | boolean>
    isEnabled?: boolean
  }): Promise<AlertConfig | null> {
    alertsLoading.value = true
    alertsError.value = null
    try {
      const newAlert = await dataService.createAlert({
        name: config.name,
        description: config.description,
        strategyType: config.strategyType,
        symbol: config.symbol,
        interval: config.interval,
        triggerType: config.triggerType || 'each_kline_close',
        params: config.params,
        isEnabled: config.isEnabled ?? true,
      })

      alerts.value.push(newAlert)
      return newAlert
    } catch (error) {
      alertsError.value = error instanceof Error ? error.message : '创建告警失败'
      console.error('createAlert error:', error)
      return null
    } finally {
      alertsLoading.value = false
    }
  }

  /**
   * 更新告警配置（使用 DataService）
   */
  async function updateAlert(
    id: string,
    config: {
      name?: string
      description?: string
      strategyType?: string
      symbol?: string
      interval?: string
      triggerType?: string
      params?: Record<string, number | boolean>
      isEnabled?: boolean
    }
  ): Promise<AlertConfig | null> {
    alertsLoading.value = true
    alertsError.value = null
    try {
      const updatedAlert = await dataService.updateAlert(id, config)

      // 更新列表中的数据
      const index = alerts.value.findIndex(a => a.id === id)
      if (index !== -1) {
        alerts.value[index] = updatedAlert
      }
      // 更新当前选中的告警
      if (currentAlert.value?.id === id) {
        currentAlert.value = updatedAlert
      }
      return updatedAlert
    } catch (error) {
      alertsError.value = error instanceof Error ? error.message : '更新告警失败'
      console.error('updateAlert error:', error)
      return null
    } finally {
      alertsLoading.value = false
    }
  }

  /**
   * 删除告警配置（使用 DataService）
   */
  async function deleteAlert(id: string): Promise<boolean> {
    alertsLoading.value = true
    alertsError.value = null
    try {
      await dataService.deleteAlert(id)

      // 从列表中移除
      alerts.value = alerts.value.filter(a => a.id !== id)
      // 清除当前选中
      if (currentAlert.value?.id === id) {
        currentAlert.value = null
      }

      // 重新订阅剩余告警的信号（删除告警后取消该告警的订阅）
      subscribeToAlertSignalEvents()

      return true
    } catch (error) {
      alertsError.value = error instanceof Error ? error.message : '删除告警失败'
      console.error('deleteAlert error:', error)
      return false
    } finally {
      alertsLoading.value = false
    }
  }

  /**
   * 启用告警（使用 DataService）
   */
  async function enableAlert(id: string): Promise<boolean> {
    alertsLoading.value = true
    alertsError.value = null
    try {
      const result = await dataService.enableAlert(id)

      // 更新本地状态
      const index = alerts.value.findIndex(a => a.id === id)
      if (index !== -1) {
        alerts.value[index] = { ...alerts.value[index], isEnabled: result.isEnabled }
      }
      return true
    } catch (error) {
      // 如果请求失败，刷新列表以确保 UI 与数据库同步
      console.warn('enableAlert failed, refreshing list:', error)
      await fetchAlerts()
      // 检查数据库中的实际状态
      const alert = alerts.value.find(a => a.id === id)
      if (alert?.isEnabled === true) {
        console.log('Alert enabled in database, marking as success')
        return true
      }
      alertsError.value = error instanceof Error ? error.message : '启用告警失败'
      console.error('enableAlert error:', error)
      return false
    } finally {
      alertsLoading.value = false
    }
  }

  /**
   * 禁用告警（使用 DataService）
   */
  async function disableAlert(id: string): Promise<boolean> {
    alertsLoading.value = true
    alertsError.value = null
    try {
      const result = await dataService.disableAlert(id)

      // 更新本地状态
      const index = alerts.value.findIndex(a => a.id === id)
      if (index !== -1) {
        alerts.value[index] = { ...alerts.value[index], isEnabled: result.isEnabled }
      }
      return true
    } catch (error) {
      // 如果请求失败，刷新列表以确保 UI 与数据库同步
      console.warn('disableAlert failed, refreshing list:', error)
      await fetchAlerts()
      // 检查数据库中的实际状态
      const alert = alerts.value.find(a => a.id === id)
      if (alert?.isEnabled === false) {
        console.log('Alert disabled in database, marking as success')
        return true
      }
      alertsError.value = error instanceof Error ? error.message : '禁用告警失败'
      console.error('disableAlert error:', error)
      return false
    } finally {
      alertsLoading.value = false
    }
  }

  /**
   * 切换告警启用/禁用状态
   */
  async function toggleAlert(id: string): Promise<boolean> {
    const alert = alerts.value.find(a => a.id === id)
    if (!alert) return false
    if (alert.isEnabled) {
      return await disableAlert(id)
    } else {
      return await enableAlert(id)
    }
  }

  /**
   * 清除错误状态
   */
  function clearError() {
    alertsError.value = null
    alertSignalsError.value = null
  }

  // ==================== 告警信号查询 Actions ====================

  /**
   * 查询告警信号列表（使用 DataService）
   */
  async function fetchAlertSignals(params?: SignalRecordQueryParams): Promise<{ items: SignalRecord[]; total: number } | null> {
    alertSignalsLoading.value = true
    alertSignalsError.value = null

    // 合并查询参数
    if (params) {
      alertSignalQueryParams.value = { ...alertSignalQueryParams.value, ...params }
    }

    try {
      const qp = alertSignalQueryParams.value

      const signals = await dataService.listSignals({
        page: qp.page,
        pageSize: qp.pageSize,
        symbol: qp.symbol,
        strategyType: qp.strategyType,
        interval: qp.interval ? String(qp.interval) : undefined,
        fromTime: qp.fromTime,
        toTime: qp.toTime,
      })

      alertSignals.value = signals
      return { items: signals, total: signals.length }
    } catch (error) {
      alertSignalsError.value = error instanceof Error ? error.message : '获取告警信号列表失败'
      console.error('fetchAlertSignals error:', error)
      return null
    } finally {
      alertSignalsLoading.value = false
    }
  }

  /**
   * 设置告警信号查询筛选条件
   */
  function setAlertSignalFilter(filter: Partial<SignalRecordQueryParams>) {
    alertSignalQueryParams.value = { ...alertSignalQueryParams.value, ...filter, page: 1 }
  }

  /**
   * 清空告警信号筛选条件
   */
  function clearAlertSignalFilter() {
    alertSignalQueryParams.value = {
      page: 1,
      pageSize: 20,
      orderBy: 'computedAt',
      orderDir: 'desc',
    }
  }

  // ==================== 实时告警信号 ====================

  /**
   * 订阅告警信号事件（使用 DataService）
   */
  function subscribeToAlertSignalEvents() {
    // 取消之前的订阅
    if (signalUnsubscribe) {
      signalUnsubscribe()
      signalUnsubscribe = null
    }

    // 获取所有告警ID
    const alertIds = alerts.value.map(alert => alert.id)

    if (alertIds.length === 0) {
      return
    }

    // 使用 DataService 批量订阅信号
    signalUnsubscribe = dataService.subscribeAllSignals(alertIds, (signal) => {
      console.log('[AlertStore] 收到实时信号:', JSON.stringify(signal, null, 2))
      addRealtimeAlertSignal(signal)
    })
  }

  /**
   * 添加实时告警信号到列表
   */
  function addRealtimeAlertSignal(signal: SignalRecord) {
    // 添加到实时信号列表头部
    realtimeAlertSignals.value.unshift(signal)

    // 限制列表长度
    if (realtimeAlertSignals.value.length > maxRealtimeAlertSignals) {
      realtimeAlertSignals.value = realtimeAlertSignals.value.slice(0, maxRealtimeAlertSignals)
    }

    // 触发告警回调（用于弹窗和声音）
    if (onSignalCallback.value) {
      onSignalCallback.value(signal)
    }
  }

  /**
   * 设置告警信号回调
   */
  function setSignalCallback(callback: (signal: SignalRecord) => void) {
    onSignalCallback.value = callback
  }

  /**
   * 手动触发测试告警信号（用于测试弹窗和声音）
   */
  function triggerTestSignal() {
    const testSignal: SignalRecord = {
      id: Date.now(),
      alertId: 'test-alert',
      name: '测试告警',
      strategyType: '测试策略',
      symbol: 'BTCUSDT',
      interval: '60',
      triggerType: 'price_above',
      signalValue: true,
      signalReason: '测试触发',
      computedAt: new Date().toISOString(),
      sourceSubscriptionKey: undefined,
      metadata: {},
    }
    addRealtimeAlertSignal(testSignal)
  }

  /**
   * 清空实时告警信号列表
   */
  function clearRealtimeAlertSignals() {
    realtimeAlertSignals.value = []
  }

  // ==================== 生命周期 ====================

  /**
   * 初始化 Store
   */
  let initialized = false
  async function initialize() {
    // 防止重复初始化
    if (initialized) {
      console.debug('[AlertStore] 已初始化，跳过重复初始化')
      return
    }
    initialized = true
    console.debug('[AlertStore] 初始化 Store')

    try {
      // 连接 DataService
      await dataService.connect()
      wsConnected.value = dataService.isConnected

      // 获取数据
      await fetchAlerts()
      await fetchAlertSignals()
    } catch (error) {
      console.error('[AlertStore] 初始化失败:', error)
      alertsError.value = error instanceof Error ? error.message : '初始化失败'
    }
  }

  /**
   * 重置 Store
   */
  function reset() {
    alerts.value = []
    alertsLoading.value = false
    alertsError.value = null
    currentAlert.value = null
    alertSignals.value = []
    alertSignalsLoading.value = false
    alertSignalsError.value = null
    realtimeAlertSignals.value = []

    // 取消信号订阅
    if (signalUnsubscribe) {
      signalUnsubscribe()
      signalUnsubscribe = null
    }
  }

  return {
    // ==================== 状态 ====================
    alerts,
    alertsLoading,
    alertsError,
    currentAlert,
    alertSignals,
    alertSignalsLoading,
    alertSignalsError,
    alertSignalQueryParams,
    wsConnected,
    realtimeAlertSignals,
    realtimeAlertSignalsCount,

    // ==================== 计算属性 ====================
    enabledAlerts,

    // ==================== 告警配置 Actions ====================
    fetchAlerts,
    fetchAlert,
    createAlert,
    updateAlert,
    deleteAlert,
    enableAlert,
    disableAlert,
    toggleAlert,
    clearError,

    // ==================== 告警信号查询 Actions ====================
    fetchAlertSignals,
    setAlertSignalFilter,
    clearAlertSignalFilter,

    // ==================== 实时信号 Actions ====================
    clearRealtimeAlertSignals,
    setSignalCallback,
    triggerTestSignal,

    // ==================== 生命周期 ====================
    initialize,
    reset,
  }
})
