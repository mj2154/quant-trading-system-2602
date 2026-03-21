<script setup lang="ts">
/**
 * 步进按钮组件
 *
 * 使用 Naive UI 按钮实现的步进按钮，与 NumberInput 配合使用
 */
import { NButton } from 'naive-ui'

interface Props {
  theme?: 'buy' | 'sell' | 'default'
  disabled?: boolean
  vertical?: boolean  // true: 垂直排列, false: 水平排列
}

const props = withDefaults(defineProps<Props>(), {
  theme: 'default',
  disabled: false,
  vertical: true,
})

const emit = defineEmits<{
  (e: 'increment'): void
  (e: 'decrement'): void
}>()
</script>

<template>
  <div :class="['stepper-buttons', { vertical }]">
    <NButton
      size="small"
      quaternary
      :disabled="disabled"
      :class="['stepper-btn', theme]"
      @click="emit('increment')"
      tabindex="-1"
    >
      <template #icon>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
        </svg>
      </template>
    </NButton>
    <NButton
      size="small"
      quaternary
      :disabled="disabled"
      :class="['stepper-btn', theme]"
      @click="emit('decrement')"
      tabindex="-1"
    >
      <template #icon>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
          <path d="M19 13H5v-2h14v2z"/>
        </svg>
      </template>
    </NButton>
  </div>
</template>

<style scoped>
.stepper-buttons {
  display: flex;
  flex-shrink: 0;
}

.stepper-buttons.vertical {
  flex-direction: column;
  gap: 2px;
}

.stepper-buttons:not(.vertical) {
  flex-direction: row;
  gap: 4px;
}

/* 通用按钮样式 */
.stepper-btn {
  width: 28px;
  height: 24px;
  border-radius: 4px;
  padding: 0;
}

.stepper-btn:not(.buy):not(.sell):not(.default) {
  background: #2a2a4a;
}

.stepper-btn:not(.buy):not(.sell):not(.default):hover:not(:disabled) {
  background: #3a3a5a;
}

/* 买入主题 */
.stepper-btn.buy {
  background: rgba(0, 192, 135, 0.2);
  color: #00c087;
}

.stepper-btn.buy:hover:not(:disabled) {
  background: rgba(0, 192, 135, 0.3);
}

.stepper-btn.buy:active:not(:disabled) {
  background: rgba(0, 192, 135, 0.4);
}

/* 卖出主题 */
.stepper-btn.sell {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.stepper-btn.sell:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.3);
}

.stepper-btn.sell:active:not(:disabled) {
  background: rgba(239, 68, 68, 0.4);
}
</style>
