<script setup lang="ts">
// Module A - K线图表模块
import TradingViewChart from '../components/TradingViewChart/index.vue'

const handleChartReady = (widget: any) => {
}

const handleChartError = (error: any) => {
}
</script>

<template>
  <div class="module module-a">
    <TradingViewChart
      height="100%"
      width="100%"
      @ready="handleChartReady"
      @error="handleChartError"
    />
  </div>
</template>

<style scoped>
.module-a {
  width: 100%;
  height: 100%;
  background-color: #1e1e1e;
}
</style>
