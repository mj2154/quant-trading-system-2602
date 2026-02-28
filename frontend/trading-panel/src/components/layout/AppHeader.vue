<script setup lang="ts">
import { h } from 'vue'
import { NButton, NDropdown, NIcon } from 'naive-ui'
import { Add } from '@vicons/ionicons5'
import { useTabStore, MODULE_CONFIG, type ModuleType } from '../../stores/tab-store'

const tabStore = useTabStore()

// 下拉菜单选项
const dropdownOptions = [
  {
    label: 'K线图表',
    key: 'module-a',
    props: {
      style: { display: 'flex', alignItems: 'center', gap: '8px' }
    }
  },
  {
    label: 'Module B',
    key: 'module-b',
  },
  {
    label: 'Module C',
    key: 'module-c',
  },
  {
    type: 'divider',
    key: 'd1',
  },
  {
    label: '账户信息',
    key: 'account-dashboard',
  },
  {
    label: '告警管理',
    key: 'alert-dashboard',
  },
  {
    label: '告警测试',
    key: 'alert-test',
  },
]

const handleSelect = (key: ModuleType) => {
  tabStore.addTab(key)
}

const handleCloseTab = (tabId: string, event: Event) => {
  event.stopPropagation()
  tabStore.closeTab(tabId)
}

const handleSwitchTab = (tabId: string) => {
  tabStore.switchTab(tabId)
}
</script>

<template>
  <header class="app-header">
    <!-- 标签列表 -->
    <div class="tabs-container">
      <div
        v-for="tab in tabStore.tabs"
        :key="tab.id"
        class="tab-item"
        :class="{ active: tab.id === tabStore.activeTabId }"
        @click="handleSwitchTab(tab.id)"
      >
        <span
          class="tab-indicator"
          :style="{ backgroundColor: MODULE_CONFIG[tab.type].color }"
        ></span>
        <span class="tab-title">{{ tab.title }}</span>
        <button
          v-if="tabStore.tabCount > 1"
          class="tab-close"
          @click="handleCloseTab(tab.id, $event)"
        >
          ×
        </button>
      </div>
    </div>

    <!-- 新建标签按钮 - 使用 Naive UI Dropdown -->
    <NDropdown
      trigger="click"
      :options="dropdownOptions"
      @select="handleSelect"
    >
      <NButton quaternary circle size="small">
        <template #icon>
          <NIcon><Add /></NIcon>
        </template>
      </NButton>
    </NDropdown>
  </header>
</template>

<style scoped>
.app-header {
  height: 40px;
  background-color: #2d2d2d;
  border-bottom: 1px solid #555;
  display: flex;
  align-items: center;
  padding: 0 8px;
  flex-shrink: 0;
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

.tab-close {
  width: 18px;
  height: 18px;
  border: none;
  background: transparent;
  color: #888;
  font-size: 14px;
  cursor: pointer;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tab-close:hover {
  background-color: #555;
  color: #fff;
}
</style>
