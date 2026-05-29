<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()

const currentTitle = computed(() => (route.meta.title as string) || '-')
</script>

<template>
  <footer class="app-footer">
    <div class="footer-left">
      <span class="footer-item">
        当前: <strong>{{ currentTitle }}</strong>
      </span>
    </div>
    <div class="footer-right">
      <span class="footer-item">QuantTrading App</span>
    </div>
  </footer>
</template>

<style scoped>
.app-footer {
  height: 24px;
  background-color: #2d2d2d;
  border-top: 1px solid #444;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  font-size: 12px;
  color: #888;
  flex-shrink: 0;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.footer-right {
  color: #666;
}

.footer-item strong {
  color: #aaa;
}
</style>
