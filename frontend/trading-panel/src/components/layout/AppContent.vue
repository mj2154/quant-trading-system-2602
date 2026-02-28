<script setup lang="ts">
import { computed } from 'vue'
import { useTabStore } from '../../stores/tab-store'
import ModuleA from '../../views/ModuleA.vue'
import ModuleB from '../../views/ModuleB.vue'
import ModuleC from '../../views/ModuleC.vue'
import AlertDashboard from '../../views/AlertDashboard.vue'
import AccountDashboard from '../../views/AccountDashboard.vue'
import AlertTest from '../../views/AlertTest.vue'

const tabStore = useTabStore()

// 当前激活的模块类型
const activeModuleType = computed(() => tabStore.activeTab?.type || null)
</script>

<template>
  <main class="app-content">
    <!-- 所有组件始终渲染，仅通过 v-show 控制显示 -->
    <ModuleA v-show="activeModuleType === 'module-a'" />
    <ModuleB v-show="activeModuleType === 'module-b'" />
    <ModuleC v-show="activeModuleType === 'module-c'" />
    <AccountDashboard v-show="activeModuleType === 'account-dashboard'" />
    <AlertDashboard v-show="activeModuleType === 'alert-dashboard'" />
    <AlertTest v-show="activeModuleType === 'alert-test'" />
  </main>
</template>

<style scoped>
.app-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* 所有组件都占据全屏容器 */
.app-content > :deep(*) {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}
</style>
