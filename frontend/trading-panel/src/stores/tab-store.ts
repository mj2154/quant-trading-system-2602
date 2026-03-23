import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// 模块类型
export type ModuleType = 'kline-chart' | 'module-b' | 'module-c' | 'alert-dashboard' | 'account-dashboard' | 'alert-test' | 'trading-dashboard'

// 标签页接口
export interface Tab {
  id: string
  title: string
  type: ModuleType
}

// 模块配置
export const MODULE_CONFIG: Record<ModuleType, { title: string; color: string; keepAlive?: boolean }> = {
  'kline-chart': { title: 'K线图表', color: '#e74c3c' },
  'module-b': { title: 'Module B', color: '#2ecc71', keepAlive: true },
  'module-c': { title: 'Module C', color: '#3498db', keepAlive: true },
  'alert-dashboard': { title: '告警管理', color: '#e67e22' },
  'account-dashboard': { title: '账户信息', color: '#9b59b6', keepAlive: true },
  'alert-test': { title: '告警测试', color: '#f39c12', keepAlive: true },
  'trading-dashboard': { title: '交易面板', color: '#00cec9', keepAlive: true },
}

// 生成唯一ID
const generateId = () => `tab-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

export const useTabStore = defineStore('tabs', () => {
  // 状态
  const tabs = ref<Tab[]>([])
  const activeTabId = ref<string | null>(null)

  // 计算属性
  const activeTab = computed(() => {
    if (!activeTabId.value) return null
    return tabs.value.find(tab => tab.id === activeTabId.value) || null
  })

  const tabCount = computed(() => tabs.value.length)

  // 添加标签页（单例模式：同类型模块只能有一个）
  const addTab = (type: ModuleType = 'kline-chart') => {
    const existingTab = tabs.value.find(tab => tab.type === type)
    if (existingTab) {
      activeTabId.value = existingTab.id
      return existingTab
    }

    const config = MODULE_CONFIG[type]
    const newTab: Tab = {
      id: generateId(),
      title: config.title,
      type,
    }
    tabs.value.push(newTab)
    activeTabId.value = newTab.id
    return newTab
  }

  // 关闭标签页
  const closeTab = (tabId: string) => {
    if (tabs.value.length <= 1) {
      return false
    }

    const index = tabs.value.findIndex(tab => tab.id === tabId)
    if (index === -1) return false

    if (activeTabId.value === tabId) {
      const nextIndex = index > 0 ? index - 1 : 1
      activeTabId.value = tabs.value[nextIndex]?.id || null
    }

    tabs.value.splice(index, 1)
    return true
  }

  // 切换标签页
  const switchTab = (tabId: string) => {
    const tab = tabs.value.find(t => t.id === tabId)
    if (tab) {
      activeTabId.value = tabId
      return true
    }
    return false
  }

  // 初始化（创建默认标签页）
  const initialize = () => {
    if (tabs.value.length === 0) {
      addTab('kline-chart')
    }
  }

  // 重置
  const reset = () => {
    tabs.value = []
    activeTabId.value = null
  }

  return {
    // 状态
    tabs,
    activeTabId,
    activeTab,
    tabCount,

    // 动作
    addTab,
    closeTab,
    switchTab,
    initialize,
    reset,
  }
})
