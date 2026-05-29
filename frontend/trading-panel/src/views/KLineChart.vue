<script setup lang="ts">
import { onActivated, onDeactivated, onBeforeUnmount } from 'vue'
import { useChartPersistenceStore } from '../stores/chart-persistence-store'

defineOptions({ name: 'KlineChart' })

const store = useChartPersistenceStore()

onActivated(() => {
  store.show()
})

onDeactivated(() => {
  store.hide()
})

onBeforeUnmount(() => {
  store.hide()
})
</script>

<template>
  <div class="module kline-chart" />
</template>

<style scoped>
.kline-chart {
  width: 100%;
  height: 100%;
  background-color: #1e1e1e;
}
</style>
