<script setup lang="ts">
// Module B - 绿色测试模块
</script>

<template>
  <div class="module module-b">
    <h1>Module B</h1>
    <p>绿色测试模块</p>
  </div>
</template>

<style scoped>
.module-b {
  background-color: #2ecc71;
}

.module {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.module h1 {
  font-size: 48px;
  margin-bottom: 16px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.module p {
  font-size: 18px;
  opacity: 0.9;
}
</style>
