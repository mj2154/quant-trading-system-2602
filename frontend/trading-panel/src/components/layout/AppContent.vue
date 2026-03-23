<script setup lang="ts">
import { computed } from 'vue'
import { useTabStore, MODULE_CONFIG } from '../../stores/tab-store'
import KLineChart from '../../views/KLineChart.vue'
import ModuleB from '../../views/ModuleB.vue'
import ModuleC from '../../views/ModuleC.vue'
import AlertDashboard from '../../views/AlertDashboard.vue'
import AccountDashboard from '../../views/AccountDashboard.vue'
import AlertTest from '../../views/AlertTest.vue'
import TradingDashboard from '../../views/TradingDashboard.vue'

const tabStore = useTabStore()

// 当前激活的模块类型
const activeModuleType = computed(() => tabStore.activeTab?.type || null)

// 组件映射
const componentMap = {
  'kline-chart': KLineChart,
  'module-b': ModuleB,
  'module-c': ModuleC,
  'alert-dashboard': AlertDashboard,
  'account-dashboard': AccountDashboard,
  'alert-test': AlertTest,
  'trading-dashboard': TradingDashboard,
} as const

// 当前激活的组件
const activeComponent = computed(() => {
  const type = activeModuleType.value
  return type ? componentMap[type] : null
})

// 当前组件是否需要 keep-alive 缓存
const isKeepAlive = computed(() => {
  const type = activeModuleType.value
  return type ? MODULE_CONFIG[type]?.keepAlive : false
})

// 当前组件是否始终运行（不能销毁）
const isAlwaysOn = computed(() => {
  const type = activeModuleType.value
  return type === 'kline-chart' || type === 'alert-dashboard'
})

// keep-alive 缓存控制：根据 MODULE_CONFIG.keepAlive 动态生成 include 数组
const keepAliveInclude = computed(() => {
  return tabStore.tabs
    .filter(tab => MODULE_CONFIG[tab.type]?.keepAlive)
    .map(tab => tab.type.split('-').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(''))
})
</script>

<template>
  <main class="app-content">
    <!-- 始终运行的组件：用 v-show 保持存活，不经过 keep-alive -->
    <KLineChart v-show="activeModuleType === 'kline-chart'" />
    <AlertDashboard v-show="activeModuleType === 'alert-dashboard'" />

    <!-- 需要 keep-alive 的页面：用动态组件 + keep-alive -->
    <keep-alive :include="keepAliveInclude">
      <component :is="activeComponent" v-if="isKeepAlive && activeComponent" />
    </keep-alive>

    <!-- 其他页面：用普通动态组件，切换时销毁重建 -->
    <component :is="activeComponent" v-if="!isKeepAlive && !isAlwaysOn && activeComponent" />
  </main>
</template>

<style scoped>
.app-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* 大多数组件占据全屏容器 */
.app-content > :deep(*:not(.trading-dashboard)) {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

/* TradingDashboard 使用自己的滚动 - 移除绝对定位 */
.app-content > :deep(.trading-dashboard) {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}
</style>
