<script setup lang="ts">
import { useChartPersistenceStore } from '../stores/chart-persistence-store'
import TradingViewChart from './TradingViewChart/index.vue'

const store = useChartPersistenceStore()
</script>

<template>
  <div v-show="store.visible" class="persistent-chart-host">
    <TradingViewChart height="100%" width="100%" />
  </div>
</template>

<style scoped>
.persistent-chart-host {
  position: absolute;
  inset: 0;
  z-index: 10;
}
</style>
