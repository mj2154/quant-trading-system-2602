<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { navItems } from '../../router'

const router = useRouter()
const route = useRoute()
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
</style>
