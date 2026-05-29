<script setup lang="ts">
import { keepAliveNames } from '../../router'
</script>

<template>
  <main class="app-content">
    <router-view v-slot="{ Component }">
      <keep-alive :include="keepAliveNames">
        <component :is="Component" />
      </keep-alive>
    </router-view>
  </main>
</template>

<style scoped>
.app-content {
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
}

.app-content > :deep(*) {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}
</style>
