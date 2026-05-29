<script setup lang="ts">
import { NConfigProvider, darkTheme, NMessageProvider, NDialogProvider, NNotificationProvider } from 'naive-ui'
import { alertThemeOverrides } from './theme/alert-theme'
import AppHeader from './components/layout/AppHeader.vue'
import AppContent from './components/layout/AppContent.vue'
import AppFooter from './components/layout/AppFooter.vue'
import GlobalAlertHandler from './components/GlobalAlertHandler.vue'
import PersistentChartHost from './components/PersistentChartHost.vue'
</script>

<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="alertThemeOverrides">
    <NMessageProvider>
      <NDialogProvider>
        <NNotificationProvider :placement="'bottom-left'" :max-count="10">
          <!-- 全局告警处理器 - 始终运行 -->
          <GlobalAlertHandler />

          <div id="app-container">
            <!-- Header: 标签栏 -->
            <AppHeader />

            <!-- Content: 内容区 -->
            <div class="content-wrapper">
              <AppContent />
              <PersistentChartHost />
            </div>

            <!-- Footer: 状态栏 -->
            <AppFooter />
          </div>
        </NNotificationProvider>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style scoped>
#app-container {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
}
</style>
