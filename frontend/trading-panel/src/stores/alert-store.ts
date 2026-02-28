/**
 * 告警管理状态管理 Store
 *
 * 管理告警配置列表、告警信号历史、CRUD 操作和 WebSocket 订阅
 *
 * 使用 WebSocket 协议 (protocolVersion 2.0) 与后端通信
 * 使用 camelCase 与协议保持一致
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  AlertSignal as AlertSignalType,
  SignalRecord,
  SignalRecordListResponse as AlertSignalListResponse,
  SignalRecordQueryParams,
  AlertTriggerType,
  AlertStrategyType,
} from '../types/alert-types'

// Re-export types for other components (only those from alert-types)
export type { SignalRecord }

// WebSocket URL
const WS_BASE_URL = 'ws://127.0.0.1:8000'

// ==================== 类型定义 ====================

/**
 * 告警配置（与后端 alert_signals 表保持一致）
 * 使用 camelCase 与 WebSocket 协议保持一致
 */
export interface AlertConfig {
  id: string
  name: string
  description: string | null
  /** 策略类型 */
  strategyType: string
  /** 交易品种 */
  symbol: string
  /** K线周期 */
  interval: string
  /** 触发类型 */
  triggerType: string
  /** 策略参数（JSONB 格式） */
  params: Record<string, number | boolean> | null
  /** 是否启用 */
  isEnabled: boolean
  createdAt: string
  updatedAt: string
  createdBy: string | null
}

/**
 * 创建告警配置请求
 */
export interface AlertConfigCreate {
  name: string
  description?: string
  strategyType: string
  symbol: string
  interval: string
  triggerType?: string
  params?: Record<string, number | boolean>
  isEnabled?: boolean
}

/**
 * 更新告警配置请求
 */
export interface AlertConfigUpdate {
  name?: string
  description?: string
  strategyType?: string
  symbol?: string
  interval?: string
  triggerType?: string
  params?: Record<string, number | boolean>
  isEnabled?: boolean
}

/**
 * WebSocket 消息基础格式 (v2.0 协议)
 */
export interface WSMessage {
  protocolVersion: string
  type: string
  requestId: string
  timestamp: number
  data: Record<string, unknown>
}

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
 * 注意：发送 到后端时会自动转换为完整参数名
 * 后端要求的参数名: macd1_fastperiod, macd1_slowperiod, macd1_signalperiod 等
 */
export const DEFAULT_PARAMS = {
  fast1: 12,
  slow1: 26,
  signal1: 9,
  fast2: 5,
  slow2: 10,
  signal2: 4,
}

/**
 * requestId 生成器
 */
let requestIdCounter = 0
function generateRequestId(prefix: string = 'req'): string {
  const timestamp = Date.now()
  requestIdCounter = (requestIdCounter + 1) % 10000
  return `${prefix}_${timestamp}_${requestIdCounter}`
}

/**
 * 生成 UUIDv4
 */
function generateUUIDv4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
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
    order_by: 'computed_at',
    order_dir: 'desc',
  })

  // WebSocket 连接
  const ws = ref<WebSocket | null>(null)
  const wsConnected = ref(false)
  const wsConnecting = ref(false)  // 防止并发创建连接
  const realtimeAlertSignals = ref<SignalRecord[]>([])
  const maxRealtimeAlertSignals = 50 // 最多保留50条实时信号

  // 待处理的请求回调 (requestId -> resolve/reject)
  const pendingRequests = new Map<string, {
    resolve: (value: unknown) => void
    reject: (reason?: unknown) => void
    timeoutId: number
  }>()

  // 告警信号到达回调 - 用于触发弹窗和声音
  const onSignalCallback = ref<((signal: SignalRecord) => void) | null>(null)

  // 请求超时时间 (毫秒)
  const REQUEST_TIMEOUT = 30000

  // ==================== 计算属性 ====================

  const enabledAlerts = computed(() =>
    alerts.value.filter(a => a.isEnabled)
  )

  const realtimeAlertSignalsCount = computed(() => realtimeAlertSignals.value.length)

  // ==================== WebSocket 基础方法 ====================

  /**
   * 发送 WebSocket 消息并等待响应
   */
  function sendWSRequest<T>(message: WSMessage): Promise<T> {
    return new Promise((resolve, reject) => {
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket 未连接'))
        return
      }

      const { requestId } = message

      // 设置超时
      const timeoutId = window.setTimeout(() => {
        pendingRequests.delete(requestId)
        reject(new Error(`请求超时: ${requestId}`))
      }, REQUEST_TIMEOUT)

      // 存储回调
      pendingRequests.set(requestId, { resolve: resolve as (value: unknown) => void, reject, timeoutId })

      // 发送消息
      ws.value.send(JSON.stringify(message))
    })
  }

  /**
   * 构建基础请求消息
   * 使用 v2.0 协议: type 字段替代 action 字段
   */
  function buildRequestMessage(data: Record<string, unknown>): WSMessage {
    // 从 data.type 获取请求类型，映射到协议请求类型
    const dataType = data.type as string
    const typeMap: Record<string, string> = {
      'list_alert_configs': 'LIST_ALERT_CONFIGS',
      'get_alert_config': 'GET_ALERT_CONFIG',
      'create_alert_config': 'CREATE_ALERT_CONFIG',
      'update_alert_config': 'UPDATE_ALERT_CONFIG',
      'delete_alert_config': 'DELETE_ALERT_CONFIG',
      'enable_alert_config': 'ENABLE_ALERT_CONFIG',
      'disable_alert_config': 'DISABLE_ALERT_CONFIG',
      'list_signals': 'LIST_SIGNALS',
    }
    return {
      protocolVersion: '2.0',
      type: typeMap[dataType] || dataType,
      requestId: generateRequestId('req_alert'),
      timestamp: Date.now(),
      data,
    }
  }

  // ==================== 告警配置 Actions ====================

  /**
   * 获取告警配置列表（使用 WebSocket）
   */
  async function fetchAlerts() {
    // 确保 WebSocket 已连接
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connectWebSocket()
      // 等待连接建立（最多等待3秒）
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (ws.value?.readyState === WebSocket.OPEN) break
      }
      // 如果仍未连接，返回错误
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        alertsError.value = 'WebSocket 连接失败，请稍后重试'
        alertsLoading.value = false
        return
      }
    }

    alertsLoading.value = true
    alertsError.value = null
    try {
      const message = buildRequestMessage({
        type: 'list_alert_configs',
        page: 1,
        pageSize: 100,
      })

      const response = await sendWSRequest<{
        items: AlertConfig[]
        total: number
        page: number
        pageSize: number
      }>(message)

      const items = response.items || []
      alerts.value = items.map((item) => ({
        ...item,
        // 确保所有必需字段都有默认值
        strategyType: item.strategyType || 'macd_resonance_v5',
        symbol: item.symbol || '',
        interval: item.interval || '60',
        triggerType: item.triggerType || 'each_kline_close',
        // 转换参数名：从完整名称 (macd1_fastperiod) 转换为简写 (fast1)
        params: convertParamsFromBackend(item.params) || { ...DEFAULT_PARAMS },
        isEnabled: item.isEnabled ?? true,
      }))

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
   * 获取单个告警配置
   */
  async function fetchAlert(id: string): Promise<AlertConfig | null> {
    // 确保 WebSocket 已连接
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connectWebSocket()
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (ws.value?.readyState === WebSocket.OPEN) break
      }
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        alertsError.value = 'WebSocket 连接失败'
        return null
      }
    }

    alertsLoading.value = true
    alertsError.value = null
    try {
      const message = buildRequestMessage({
        type: 'get_alert_config',
        id,
      })

      const data = await sendWSRequest<AlertConfig>(message)
      currentAlert.value = {
        ...data,
        strategyType: data.strategyType || 'macd',
      }
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
   * 将前端参数转换为后端API格式
   * 映射前端简化的参数名到后端要求的完整参数名
   * 后端要求的参数名: macd1_fastperiod, macd1_slowperiod, macd1_signalperiod 等
   */
  function convertParamsToBackend(params: Record<string, number | boolean> | undefined): Record<string, number | boolean> {
    // 后端要求的完整参数名映射
    const paramMapping: Record<string, string> = {
      // MACD1 参数映射
      fast1: 'macd1_fastperiod',
      slow1: 'macd1_slowperiod',
      signal1: 'macd1_signalperiod',
      // MACD2 参数映射
      fast2: 'macd2_fastperiod',
      slow2: 'macd2_slowperiod',
      signal2: 'macd2_signalperiod',
    }

    // 默认参数值（使用简写名称）
    const defaultParams = DEFAULT_PARAMS

    // 如果没有传入参数，使用默认值并转换
    if (!params) {
      const converted: Record<string, number | boolean> = {}
      for (const [key, value] of Object.entries(defaultParams)) {
        converted[paramMapping[key] || key] = value
      }
      return converted
    }

    // 从默认参数开始，然后应用用户传入的参数
    const converted: Record<string, number | boolean> = {}

    // 首先设置默认值
    for (const [key, value] of Object.entries(defaultParams)) {
      converted[paramMapping[key] || key] = value
    }

    // 然后用用户传入的值覆盖
    for (const [key, value] of Object.entries(params)) {
      // 如果是简写名称，转换为完整名称
      if (key in paramMapping) {
        converted[paramMapping[key]] = value
      } else {
        // 如果已经是完整名称或未知参数，直接使用
        converted[key] = value
      }
    }

    return converted
  }

  /**
   * 将后端返回的参数转换为前端显示格式
   * 从完整参数名 (macd1_fastperiod) 转换为简写 (fast1)
   */
  function convertParamsFromBackend(params: Record<string, number | boolean> | undefined | null): Record<string, number | boolean> {
    // 后端参数名到简写的映射
    const paramReverseMapping: Record<string, string> = {
      // MACD1 参数
      macd1_fastperiod: 'fast1',
      macd1_slowperiod: 'slow1',
      macd1_signalperiod: 'signal1',
      // MACD2 参数
      macd2_fastperiod: 'fast2',
      macd2_slowperiod: 'slow2',
      macd2_signalperiod: 'signal2',
    }

    // 如果没有参数，返回默认值
    if (!params) {
      return { ...DEFAULT_PARAMS }
    }

    const converted: Record<string, number | boolean> = {}

    for (const [key, value] of Object.entries(params)) {
      // 如果是完整名称，转换为简写
      if (key in paramReverseMapping) {
        converted[paramReverseMapping[key]] = value
      } else {
        // 否则直接使用
        converted[key] = value
      }
    }

    // 如果转换后为空，返回默认值
    if (Object.keys(converted).length === 0) {
      return { ...DEFAULT_PARAMS }
    }

    return converted
  }

  /**
   * 创建告警配置
   */
  async function createAlert(config: AlertConfigCreate): Promise<AlertConfig | null> {
    // 确保 WebSocket 已连接
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connectWebSocket()
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (ws.value?.readyState === WebSocket.OPEN) break
      }
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        alertsError.value = 'WebSocket 连接失败，请稍后重试'
        return null
      }
    }

    alertsLoading.value = true
    alertsError.value = null
    try {
      // 转换告警格式到 API 格式
      const alertData = {
        type: 'create_alert_config',
        id: generateUUIDv4(),
        name: config.name,
        description: config.description || '',
        triggerType: config.triggerType || 'each_kline_close',
        symbol: config.symbol,
        interval: config.interval,
        isEnabled: config.isEnabled ?? true,
        // 转换参数名称：前端可能使用简写或完整名称
        params: convertParamsToBackend(config.params),
        // 使用用户传入的 strategyType，或使用默认值
        strategyType: config.strategyType || 'macd_resonance_v5',
        // 添加 created_by 字段
        created_by: 'user_001',
      }

      console.log('[AlertStore] 创建告警配置，发送数据:', JSON.stringify(alertData, null, 2))

      const message = buildRequestMessage(alertData)
      const data = await sendWSRequest<AlertConfig>(message)

      const newAlert: AlertConfig = {
        ...data,
        strategyType: data.strategyType || alertData.strategyType,
        symbol: data.symbol || config.symbol,
        interval: data.interval || config.interval,
        // 转换参数格式：从后端完整名称 (macd1_fastperiod) 转换为前端简写 (fast1)
        params: convertParamsFromBackend(data.params) || convertParamsToBackend(config.params),
      }
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
   * 更新告警配置
   */
  async function updateAlert(id: string, config: AlertConfigUpdate): Promise<AlertConfig | null> {
    // 确保 WebSocket 已连接
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connectWebSocket()
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (ws.value?.readyState === WebSocket.OPEN) break
      }
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        alertsError.value = 'WebSocket 连接失败'
        return null
      }
    }

    alertsLoading.value = true
    alertsError.value = null
    try {
      // 构建更新数据
      const alertData: Record<string, unknown> = {
        type: 'update_alert_config',
        id,
      }
      if (config.name !== undefined) alertData.name = config.name
      if (config.description !== undefined) alertData.description = config.description
      if (config.triggerType !== undefined) alertData.triggerType = config.triggerType
      if (config.symbol !== undefined) alertData.symbol = config.symbol
      if (config.interval !== undefined) alertData.interval = config.interval
      if (config.isEnabled !== undefined) alertData.isEnabled = config.isEnabled
      if (config.params !== undefined) alertData.params = config.params
      if (config.strategyType !== undefined) alertData.strategyType = config.strategyType

      const message = buildRequestMessage(alertData)
      const data = await sendWSRequest<AlertConfig>(message)

      const updatedAlert: AlertConfig = {
        ...data,
        // 转换参数格式：从后端完整名称 (macd1_fastperiod) 转换为前端简写 (fast1)
        params: convertParamsFromBackend(data.params),
      }
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
   * 删除告警配置
   */
  async function deleteAlert(id: string): Promise<boolean> {
    // 确保 WebSocket 已连接
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connectWebSocket()
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (ws.value?.readyState === WebSocket.OPEN) break
      }
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        alertsError.value = 'WebSocket 连接失败'
        return false
      }
    }

    alertsLoading.value = true
    alertsError.value = null
    try {
      const message = buildRequestMessage({
        type: 'delete_alert_config',
        id,
      })

      await sendWSRequest<void>(message)

      // 从列表中移除
      alerts.value = alerts.value.filter(a => a.id !== id)
      // 清除当前选中
      if (currentAlert.value?.id === id) {
        currentAlert.value = null
      }
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
   * 启用告警
   */
  async function enableAlert(id: string): Promise<boolean> {
    alertsLoading.value = true
    alertsError.value = null
    try {
      const message = buildRequestMessage({
        type: 'enable_alert_config',
        id,
        isEnabled: true,  // Backend requires this field
      })

      const data = await sendWSRequest<{ isEnabled: boolean }>(message)

      // 更新本地状态
      const index = alerts.value.findIndex(a => a.id === id)
      if (index !== -1) {
        alerts.value[index] = { ...alerts.value[index], isEnabled: data.isEnabled }
      }
      return true
    } catch (error) {
      // 如果请求失败，仍然刷新列表以确保 UI 与数据库同步
      // (数据库可能已更新，但响应未能送达)
      console.warn('enableAlert failed, refreshing list:', error)
      await fetchAlerts()
      // 检查数据库中的实际状态
      const alert = alerts.value.find(a => a.id === id)
      if (alert?.isEnabled === true) {
        // 数据库已更新，但响应超时，视为成功
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
   * 禁用告警
   */
  async function disableAlert(id: string): Promise<boolean> {
    alertsLoading.value = true
    alertsError.value = null
    try {
      const message = buildRequestMessage({
        type: 'disable_alert_config',
        id,
        isEnabled: false,  // Backend requires this field
      })

      const data = await sendWSRequest<{ isEnabled: boolean }>(message)

      // 更新本地状态
      const index = alerts.value.findIndex(a => a.id === id)
      if (index !== -1) {
        alerts.value[index] = { ...alerts.value[index], isEnabled: data.isEnabled }
      }
      return true
    } catch (error) {
      // 如果请求失败，仍然刷新列表以确保 UI 与数据库同步
      // (数据库可能已更新，但响应未能送达)
      console.warn('disableAlert failed, refreshing list:', error)
      await fetchAlerts()
      // 检查数据库中的实际状态
      const alert = alerts.value.find(a => a.id === id)
      if (alert?.isEnabled === false) {
        // 数据库已更新，但响应超时，视为成功
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
   * 查询告警信号列表
   */
  async function fetchAlertSignals(params?: SignalRecordQueryParams): Promise<AlertSignalListResponse | null> {
    // 确保 WebSocket 已连接
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      connectWebSocket()
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (ws.value?.readyState === WebSocket.OPEN) break
      }
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        alertSignalsError.value = 'WebSocket 连接失败'
        alertSignalsLoading.value = false
        return null
      }
    }

    alertSignalsLoading.value = true
    alertSignalsError.value = null

    // 合并查询参数
    if (params) {
      alertSignalQueryParams.value = { ...alertSignalQueryParams.value, ...params }
    }

    try {
      const qp = alertSignalQueryParams.value

      const message = buildRequestMessage({
        type: 'list_signals',
        page: qp.page || 1,
        pageSize: qp.pageSize || 20,
        symbol: qp.symbol,
        strategyType: qp.strategyType,
        interval: qp.interval,
        from_time: qp.from_time,
        to_time: qp.to_time,
        order_by: qp.order_by,
        order_dir: qp.order_dir,
      })

      const data = await sendWSRequest<AlertSignalListResponse>(message)

      alertSignals.value = data.items
      return data
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
      order_by: 'computed_at',
      order_dir: 'desc',
    }
  }

  // ==================== WebSocket 实时告警信号 ====================

  /**
   * 连接 WebSocket 并订阅告警信号事件
   */
  function connectWebSocket() {
    // 如果已连接或正在连接，直接返回
    if (ws.value?.readyState === WebSocket.OPEN) {
      return
    }
    if (wsConnecting.value) {
      return
    }

    wsConnecting.value = true

    try {
      ws.value = new WebSocket(`${WS_BASE_URL}/ws/market`)

      ws.value.onopen = () => {
        const isReconnect = wsConnected.value === false && ws.value !== null
        wsConnected.value = true
        wsConnecting.value = false
        console.log('[AlertStore] WebSocket connected', isReconnect ? '(reconnect)' : '(new)')

        // 如果是重连且已有告警配置，需要重新订阅信号
        if (isReconnect && alerts.value.length > 0) {
          console.log('[AlertStore] 重连后重新订阅信号')
          subscribeToAlertSignalEvents()
        }
        // 注意：新连接时不在这里立即订阅，等 fetchAlerts() 完成后统一订阅
      }

      ws.value.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          // 调试日志：打印所有收到的消息 (v2.0 协议: type === 'UPDATE')
          if (message.type === 'UPDATE') {
            console.log('[AlertStore] 收到实时更新:', JSON.stringify(message, null, 2))
          }
          handleWebSocketMessage(message)
        } catch (error) {
          console.error('[AlertStore] Failed to parse WebSocket message:', error)
        }
      }

      ws.value.onerror = (error) => {
        console.error('[AlertStore] WebSocket error:', error)
        wsConnecting.value = false
      }

      ws.value.onclose = () => {
        wsConnected.value = false
        wsConnecting.value = false
        console.log('[AlertStore] WebSocket disconnected')
        // 自动重连
        setTimeout(connectWebSocket, 3000)
      }
    } catch (error) {
      console.error('[AlertStore] Failed to create WebSocket:', error)
      wsConnecting.value = false
    }
  }

  /**
   * 订阅告警信号事件
   * 使用精确订阅键 SIGNAL:{alert_id} 而非通配符
   */
  function subscribeToAlertSignalEvents() {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
      return
    }

    // 订阅告警信号事件 - 使用精确订阅键
    // 订阅所有已创建告警的信号
    const subscriptions = alerts.value.map(alert => `SIGNAL:${alert.id}`)

    // 注意：必须包含 protocolVersion 和 timestamp 字段（后端 parse_message 需要）
    // subscriptions 必须在 data 内部（遵循协议规范）
    // 使用 v2.0 协议: type 字段替代 action 字段
    const subscribeMessage = {
      protocolVersion: '2.0',
      type: 'SUBSCRIBE',
      timestamp: Date.now(),
      data: {
        subscriptions,
      },
    }

    console.log('[AlertStore] 订阅告警信号事件:', JSON.stringify(subscribeMessage, null, 2))
    ws.value.send(JSON.stringify(subscribeMessage))
  }

  /**
   * 处理 WebSocket 消息
   * 遵循三阶段响应模式 (v2.0 协议):
   * 1. 客户端发送请求
   * 2. 服务器返回 ACK 确认（立即响应）
   * 3. 服务器返回具体数据类型或 ERROR 响应（最终结果）
   */
  function handleWebSocketMessage(message: Record<string, unknown>) {
    const msgType = message.type as string
    const requestId = message.requestId as string

    // 处理 ACK 确认响应（第一阶段）
    // 服务器收到请求后立即返回 ACK，确认请求已被接收
    // 需要继续等待具体数据类型响应
    if (msgType === 'ACK') {
      console.log('[AlertStore] 收到 ACK 确认, requestId:', requestId)
      // ACK 不解决 Promise，只是确认请求已被接收
      // 继续等待数据类型响应
      return
    }

    // 处理请求响应（最终阶段）- v2.0 使用具体数据类型
    // 成功响应使用 ALERT_CONFIG_DATA, SIGNAL_DATA 等
    if (msgType === 'ALERT_CONFIG_DATA' || msgType === 'SIGNAL_DATA' || msgType === 'ERROR') {
      const pending = pendingRequests.get(requestId)
      if (pending) {
        // 清除超时
        clearTimeout(pending.timeoutId)
        pendingRequests.delete(requestId)

        if (msgType === 'ALERT_CONFIG_DATA' || msgType === 'SIGNAL_DATA') {
          pending.resolve(message.data)
        } else {
          // Backend sends: { errorCode, errorMessage }
          // Frontend was looking for: message
          const errorData = message.data as Record<string, unknown>
          const errorMsg = (errorData?.errorMessage || errorData?.message || 'Unknown error') as string
          pending.reject(errorMsg)
        }
        return
      }
    }

    // 处理实时更新消息 (v2.0 协议: type === 'UPDATE')
    if (msgType === 'UPDATE') {
      const data = message.data as Record<string, unknown>
      // subscriptionKey 在 message.data.subscriptionKey 中
      const subscriptionKey = data.subscriptionKey as string

      console.log('[AlertStore] 收到更新消息:', {
        type: msgType,
        subscriptionKey,
        dataKeys: Object.keys(data),
      })

      // 检查是否是告警信号更新 (通过 subscriptionKey 识别)
      // 设计原则：subscriptionKey: SIGNAL:xxx 已表明数据类型，无需 content.type 冗余字段
      if (subscriptionKey?.startsWith('SIGNAL:')) {
        // 信号数据在 message.data.content 中
        const content = data.content as Record<string, unknown>
        console.log('[AlertStore] 处理告警信号:', JSON.stringify(content, null, 2))

        // 转换后端数据格式到前端格式
        const signalData = transformBackendSignalToFrontend(content)
        addRealtimeAlertSignal(signalData)
      }
    }
  }

  /**
   * 转换后端信号数据到前端格式
   * 后端字段: strategyType -> 前端字段: strategy_name
   */
  function transformBackendSignalToFrontend(content: Record<string, unknown>): SignalRecord {
    return {
      id: (content.id as number) || 0,
      alert_id: (content.alert_id as string) || '',
      config_id: (content.config_id as string) || null,
      // strategyType -> strategy_name
      strategy_name: (content.strategyType as string) || (content.strategy_name as string) || 'unknown',
      symbol: (content.symbol as string) || '',
      interval: (content.interval as string) || '',
      triggerType: (content.triggerType as string) || null,
      // signal_value 可能是 boolean 或字符串 't'/'f'
      signal_value: content.signal_value === 't' ? true : content.signal_value === 'f' ? false : content.signal_value as boolean | null,
      signal_reason: (content.signal_reason as string) || null,
      computed_at: (content.computed_at as string) || new Date().toISOString(),
      source_subscription_key: (content.source_subscription_key as string) || null,
      metadata: (content.metadata as Record<string, unknown>) || {},
    }
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
      alert_id: 'test-alert',
      config_id: null,
      strategy_name: '测试策略',
      symbol: 'BTCUSDT',
      interval: '60',
      triggerType: 'price_above',
      signal_value: true,
      signal_reason: '测试触发',
      computed_at: new Date().toISOString(),
      source_subscription_key: null,
      metadata: {},
    }
    addRealtimeAlertSignal(testSignal)
  }

  /**
   * 断开 WebSocket
   */
  function disconnectWebSocket() {
    // 清除所有待处理的请求
    for (const [_, pending] of pendingRequests) {
      clearTimeout(pending.timeoutId)
      pending.reject(new Error('WebSocket 连接关闭'))
    }
    pendingRequests.clear()

    if (ws.value) {
      ws.value.close()
      ws.value = null
      wsConnected.value = false
    }

    // 重置初始化标志，允许重新初始化
    initialized = false
  }

  /**
   * 清空实时告警信号列表
   */
  function clearRealtimeAlertSignals() {
    realtimeAlertSignals.value = []
  }

  // ==================== 初始化 ====================

  /**
   * 初始化 Store
   * 防止重复初始化导致多个 WebSocket 连接
   */
  let initialized = false
  function initialize() {
    // 防止重复初始化
    if (initialized) {
      console.debug('[AlertStore] 已初始化，跳过重复初始化')
      return
    }
    initialized = true
    console.debug('[AlertStore] 初始化 Store')

    connectWebSocket()
    // 等待 WebSocket 连接成功后获取数据
    const checkAndFetch = () => {
      if (wsConnected.value) {
        fetchAlerts()
        fetchAlertSignals()
      } else {
        setTimeout(checkAndFetch, 500)
      }
    }
    checkAndFetch()
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
    disconnectWebSocket()
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
    ws,
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

    // ==================== WebSocket Actions ====================
    connectWebSocket,
    disconnectWebSocket,
    clearRealtimeAlertSignals,
    setSignalCallback,
    triggerTestSignal,

    // ==================== 生命周期 ====================
    initialize,
    reset,
  }
})
