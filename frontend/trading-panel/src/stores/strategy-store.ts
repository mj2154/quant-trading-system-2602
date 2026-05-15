/**
 * 策略元数据 Store
 *
 * 管理策略列表和策略参数配置
 * 使用 DataService 与后端通信
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dataService } from '../services/data-service/DataService'
import type { StrategyMetadataResponse } from '../services/data-service/types'

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
 * 策略元数据 - 使用后端返回的驼峰命名格式
 */
export interface StrategyMetadata {
  type: string
  name: string
  description: string
  params: StrategyParam[]
}

// ==================== Store 定义 ====================

export const useStrategyStore = defineStore('strategy', () => {
  // ==================== 状态 ====================

  const strategies = ref<StrategyMetadata[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ==================== Actions ====================

  /**
   * 获取策略列表
   * 使用 DataService 获取数据
   */
  async function fetchStrategies() {
    loading.value = true
    error.value = null
    try {
      console.log('[StrategyStore] Fetching strategies...')
      // 通过 DataService 获取策略元数据
      const rawStrategies = await dataService.getStrategyMetadata()
      console.debug('[StrategyStore] Raw strategies received:', rawStrategies.length)

      // 转换后端返回的数据为前端格式
      strategies.value = rawStrategies.map((s: StrategyMetadataResponse) => ({
        type: s.type,
        name: s.name,
        description: s.description,
        params: s.params.map(p => ({
          name: p.name,
          type: p.type as 'int' | 'float' | 'bool',
          default: p.default,
          min: p.min,
          max: p.max,
          description: p.description,
        })),
      }))
      console.debug('[StrategyStore] Strategies loaded:', strategies.value.length)
    } catch (e) {
      console.error('[StrategyStore] Error fetching strategies:', e)
      error.value = e instanceof Error ? e.message : 'Unknown error'
      strategies.value = []
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
