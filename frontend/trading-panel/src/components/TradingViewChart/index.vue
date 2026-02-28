<template>
  <div class="tradingview-chart-wrapper">
    <!-- 图表容器 -->
    <div
      :id="containerId"
      class="tradingview-chart-container"
      :style="containerStyle"
    ></div>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="tradingview-loading">
      <div class="loading-spinner"></div>
      <p class="loading-text">{{ loadingText }}</p>
    </div>

    <!-- 错误状态 -->
    <div v-if="error" class="tradingview-error">
      <div class="error-icon">⚠️</div>
      <p class="error-message">{{ errorMessage }}</p>
      <button @click="handleRetry" class="retry-button">重试</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useTradingView } from './composables/useTradingView.js';

// Props 定义
const props = defineProps({
  // 样式配置
  height: {
    type: [String, Number],
    default: 600
  },
  width: {
    type: [String, Number],
    default: '100%'
  },

  // 加载文本
  loadingText: {
    type: String,
    default: '正在加载图表...'
  }
});

// Emits 定义
const emit = defineEmits([
  'ready',
  'error'
]);

// 响应式数据
const containerId = ref(`tv_chart_container_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
const chartInitialized = ref(false);

// 容器样式
const containerStyle = computed(() => {
  const height = typeof props.height === 'number' ? `${props.height}px` : props.height;
  const width = typeof props.width === 'number' ? `${props.width}px` : props.width;
  return {
    height,
    width
  };
});

// 使用 TradingView Composable
const {
  widget,
  isReady,
  isLoading,
  error,
  createWidget,
  destroyWidget,
  reload,
  getWidget
} = useTradingView(containerId.value);

// 错误消息
const errorMessage = computed(() => {
  if (!error.value) return '';
  return error.value.message || '图表加载失败';
});

// 监听 isReady 状态
watch(isReady, (ready) => {
  if (ready) {
    chartInitialized.value = true;
    emit('ready', getWidget());
  }
});

// 监听错误
watch(error, (err) => {
  if (err) {
    emit('error', err);
  }
});

// 重试方法
const handleRetry = () => {
  reload();
};

// 组件挂载时初始化图表
onMounted(async () => {
  await nextTick();
  createWidget();
});
</script>

<style scoped>
.tradingview-chart-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: var(--tv-chart-bg, #ffffff);
  border-radius: 8px;
  overflow: hidden;
}

.tradingview-chart-container {
  width: 100%;
  height: 100%;
}

.tradingview-loading,
.tradingview-error {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--tv-loading-bg, rgba(255, 255, 255, 0.9));
  z-index: 10;
}

.tradingview-error {
  background: var(--tv-error-bg, rgba(255, 255, 255, 0.95));
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--tv-spinner-border, #e0e0e0);
  border-top-color: var(--tv-spinner-color, #2196f3);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text,
.error-message {
  margin-top: 16px;
  color: var(--tv-text-color, #666);
  font-size: 14px;
  text-align: center;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.retry-button {
  margin-top: 16px;
  padding: 8px 24px;
  background: var(--tv-button-bg, #2196f3);
  color: var(--tv-button-color, #ffffff);
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-button:hover {
  background: var(--tv-button-hover-bg, #1976d2);
}

/* 暗色主题支持 */
:global(.dark) .tradingview-chart-wrapper {
  background: #1e1e1e;
}

:global(.dark) .tradingview-loading {
  background: rgba(30, 30, 30, 0.9);
}

:global(.dark) .tradingview-error {
  background: rgba(30, 30, 30, 0.95);
}

:global(.dark) .loading-spinner {
  border-color: #3a3a3a;
  border-top-color: #2196f3;
}

:global(.dark) .loading-text,
:global(.dark) .error-message {
  color: #e0e0e0;
}

:global(.dark) .retry-button {
  background: #2196f3;
}

:global(.dark) .retry-button:hover {
  background: #1976d2;
}
</style>
