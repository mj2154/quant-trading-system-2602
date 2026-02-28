/**
 * 策略元数据 Store
 *
 * 管理策略列表和策略参数配置
 * 使用 WebSocket 协议与后端通信
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAlertStore } from './alert-store'

// ==================== 类型定义 ====================

/**
 * 策略参数定义
 */
export interface StrategyParam {
  name: string
  type: 'int' | 'float' | 'bool'
  default: number | boolean
  min?: number
  max?: number
  description: string
}

/**
 * 策略元数据
 */
export interface StrategyMetadata {
  type: string
  name: string
  description: string
  params: StrategyParam[]
}

/**
 * API 响应格式
 */
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
}

/**
 * WebSocket 消息格式 (v2.0 协议)
 */
interface WSMessage {
  protocolVersion: string
  type: string
  requestId: string
  timestamp: number
  data: Record<string, unknown>
}

// ==================== Store 定义 ====================

export const useStrategyStore = defineStore('strategy', () => {
  // ==================== 状态 ====================

  const strategies = ref<StrategyMetadata[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ==================== 私有方法 ====================

  /**
   * 生成请求ID
   */
  function generateRequestId(prefix: string): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
  }

  /**
   * 构建 WebSocket 请求消息
   * 使用 v2.0 协议: type 字段替代 action 字段
   */
  function buildRequestMessage(data: Record<string, unknown>): WSMessage {
    // 从 data.type 获取请求类型，映射到协议请求类型
    const dataType = data.type as string
    const typeMap: Record<string, string> = {
      'get_strategy_metadata': 'GET_STRATEGY_METADATA',
      'get_strategy_metadata_by_type': 'GET_STRATEGY_METADATA_BY_TYPE',
    }
    return {
      protocolVersion: '2.0',
      type: typeMap[dataType] || dataType,
      requestId: generateRequestId('req_strategy'),
      timestamp: Date.now(),
      data,
    }
  }

  /**
   * 通过 WebSocket 发送请求
   * 复用 alertStore 的 WebSocket 连接
   */
  async function sendWSRequest<T>(message: WSMessage): Promise<T> {
    const alertStore = useAlertStore()

    // 确保 WebSocket 已连接
    if (!alertStore.ws || alertStore.ws.readyState !== WebSocket.OPEN) {
      alertStore.connectWebSocket()
      // 等待连接建立（最多等待3秒）
      for (let i = 0; i < 30; i++) {
        await new Promise(resolve => setTimeout(resolve, 100))
        if (alertStore.ws?.readyState === WebSocket.OPEN) break
      }
      // 如果仍未连接，返回错误
      if (!alertStore.ws || alertStore.ws.readyState !== WebSocket.OPEN) {
        throw new Error('WebSocket 连接失败')
      }
    }

    return new Promise((resolve, reject) => {
      const { requestId } = message
      let resolved = false

      // 设置超时
      const timeoutId = window.setTimeout(() => {
        if (!resolved) {
          resolved = true
          removeMessageListener()
          reject(new Error(`请求超时: ${requestId}`))
        }
      }, 10000)

      // 定义消息处理函数 - 使用 addEventListener 避免覆盖 onmessage
      const messageHandler = (event: MessageEvent) => {
        try {
          const response = JSON.parse(event.data)
          // 检查是否是目标请求的响应
          if (response.requestId === requestId) {
            resolved = true
            window.clearTimeout(timeoutId)
            removeMessageListener()
            // v2.0 协议: 使用 type 字段判断响应类型
            // 成功响应使用具体数据类型 (如 STRATEGY_METADATA_DATA)
            if (response.type === 'STRATEGY_METADATA_DATA') {
              resolve(response.data as T)
            } else if (response.type === 'ERROR') {
              const errorData = response.data as Record<string, unknown>
              reject(new Error((errorData?.errorMessage as string) || 'Request failed'))
            } else {
              reject(new Error('Unknown response type'))
            }
          }
          // 其他消息不处理，让 alertStore 处理
        } catch {
          // 忽略解析错误
        }
      }

      // 使用 addEventListener 添加一次性监听器
      const removeMessageListener = () => {
        alertStore.ws?.removeEventListener('message', messageHandler)
      }

      alertStore.ws!.addEventListener('message', messageHandler)

      // 发送消息
      alertStore.ws!.send(JSON.stringify(message))
    })
  }

  // ==================== Actions ====================

  /**
   * 获取策略列表
   */
  async function fetchStrategies() {
    loading.value = true
    error.value = null
    try {
      const message = buildRequestMessage({
        type: 'get_strategy_metadata',
      })

      const response = await sendWSRequest<{ strategies: StrategyMetadata[] }>(message)
      const data = response.strategies
      strategies.value = data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    } finally {
      loading.value = false
    }
  }

  /**
   * 根据策略类型获取策略元数据
   */
  function getStrategyByType(type: string): StrategyMetadata | undefined {
    return strategies.value.find(s => s.type === type)
  }

  /**
   * 获取策略参数的默认值
   */
  function getDefaultParams(strategyType: string): Record<string, number | boolean> {
    const strategy = getStrategyByType(strategyType)
    if (!strategy) {
      return {}
    }

    const params: Record<string, number | boolean> = {}
    strategy.params.forEach(param => {
      params[param.name] = param.default
    })
    return params
  }

  return {
    // ==================== 状态 ====================
    strategies,
    loading,
    error,

    // ==================== Actions ====================
    fetchStrategies,
    getStrategyByType,
    getDefaultParams,
  }
})
