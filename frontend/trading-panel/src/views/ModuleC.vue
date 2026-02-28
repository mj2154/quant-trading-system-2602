<script setup lang="ts">
// Module C - 蓝色测试模块
</script>

<template>
  <div class="module module-c">
    <h1>Module C</h1>
    <p>蓝色测试模块</p>
  </div>
</template>

<style scoped>
.module-c {
  background-color: #3498db;
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
