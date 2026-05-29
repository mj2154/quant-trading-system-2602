<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { ref, onMounted } from 'vue'
import { navItems } from '../../router'

const router = useRouter()
const route = useRoute()

const isMaximized = ref(false)

onMounted(() => {
  window.electronWindow?.isMaximized().then((val: boolean) => {
    isMaximized.value = val
  }).catch(() => {})

  window.electronWindow?.onMaximizeChanged((val: boolean) => {
    isMaximized.value = val
  })
})

function handleMinimize() {
  window.electronWindow?.minimize()
}

function handleMaximize() {
  window.electronWindow?.maximize()
}

function handleClose() {
  window.electronWindow?.close()
}
</script>

<template>
  <header class="app-header">
    <div class="tabs-container">
      <div
        v-for="item in navItems"
        :key="item.path"
        class="tab-item"
        :class="{ active: route.path === item.path }"
        @click="router.push(item.path)"
      >
        <span
          class="tab-indicator"
          :style="{ backgroundColor: item.color }"
        ></span>
        <span class="tab-title">{{ item.title }}</span>
      </div>
    </div>

    <!-- 窗口控制按钮 -->
    <div class="window-controls">
      <button class="win-btn win-btn-minimize" title="Minimize" @click="handleMinimize">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <rect x="1" y="5.5" width="10" height="1" fill="currentColor" />
        </svg>
      </button>
      <button class="win-btn win-btn-maximize" title="Maximize" @click="handleMaximize">
        <svg v-if="!isMaximized" width="12" height="12" viewBox="0 0 12 12">
          <rect x="1.5" y="1.5" width="9" height="9" rx="0.5" fill="none" stroke="currentColor" stroke-width="1" />
        </svg>
        <svg v-else width="12" height="12" viewBox="0 0 12 12">
          <rect x="2.5" y="0.5" width="8" height="8" rx="0.5" fill="none" stroke="currentColor" stroke-width="1" />
          <rect x="0.5" y="2.5" width="8" height="8" rx="0.5" fill="none" stroke="currentColor" stroke-width="1" />
        </svg>
      </button>
      <button class="win-btn win-btn-close" title="Close" @click="handleClose">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <line x1="1" y1="1" x2="11" y2="11" stroke="currentColor" stroke-width="1.2" />
          <line x1="1" y1="11" x2="11" y2="1" stroke="currentColor" stroke-width="1.2" />
        </svg>
      </button>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: 40px;
  background-color: #2d2d2d;
  border-bottom: 1px solid #555;
  display: flex;
  align-items: center;
  padding: 0 0 0 8px;
  flex-shrink: 0;
  -webkit-app-region: drag;
}

.tabs-container {
  display: flex;
  flex: 1;
  overflow-x: auto;
  gap: 2px;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background-color: #3c3c3c;
  border-radius: 4px 4px 0 0;
  cursor: pointer;
  min-width: 100px;
  max-width: 180px;
  transition: background-color 0.15s;
  -webkit-app-region: no-drag;
}

.tab-item:hover {
  background-color: #4a4a4a;
}

.tab-item.active {
  background-color: #1e1e1e;
}

.tab-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tab-title {
  flex: 1;
  font-size: 13px;
  color: #ccc;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-item.active .tab-title {
  color: #fff;
}

/* 窗口控制按钮 */
.window-controls {
  display: flex;
  height: 100%;
  -webkit-app-region: no-drag;
}

.win-btn {
  width: 46px;
  height: 100%;
  border: none;
  border-radius: 0;
  background: transparent;
  color: #999;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.12s, color 0.12s;
}

.win-btn:hover {
  background-color: #4a4a4a;
  color: #ddd;
}

.win-btn-close:hover {
  background-color: #e81123;
  color: #fff;
}
</style>
