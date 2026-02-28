<template>
  <div class="realtime-signals">
    <!-- 标题栏 -->
    <div class="header">
      <div class="title">
        <span>实时信号</span>
        <n-tag :type="store.wsConnected ? 'success' : 'error'" size="small">
          {{ store.wsConnected ? '已连接' : '未连接' }}
        </n-tag>
      </div>
      <div class="actions">
        <n-button size="tiny" quaternary @click="store.clearRealtimeAlertSignals">清空</n-button>
      </div>
    </div>

    <!-- 信号列表 -->
    <div v-if="store.realtimeAlertSignals.length > 0" class="signal-stream">
      <TransitionGroup name="signal">
        <div
          v-for="signal in store.realtimeAlertSignals"
          :key="signal.id"
          class="signal-item"
          :class="{
            'signal-long': signal.signal_value === true,
            'signal-short': signal.signal_value === false,
            'signal-none': signal.signal_value === null,
          }"
        >
          <div class="signal-icon">
            <n-icon v-if="signal.signal_value === true" size="18" color="#18a058">
              <ArrowUpIcon />
            </n-icon>
            <n-icon v-else-if="signal.signal_value === false" size="18" color="#d03050">
              <ArrowDownIcon />
            </n-icon>
            <n-icon v-else size="18" color="#909399">
              <MinusIcon />
            </n-icon>
          </div>
          <div class="signal-content">
            <div class="signal-header">
              <span class="strategy-name">{{ signal.strategy_name }}</span>
              <span class="signal-type">
                {{ signal.signal_value === true ? '做多' : signal.signal_value === false ? '做空' : '无' }}
              </span>
            </div>
            <div class="signal-info">
              <span class="symbol">{{ signal.symbol }}</span>
              <span class="interval">{{ formatInterval(signal.interval) }}</span>
            </div>
            <div v-if="signal.signal_reason" class="signal-reason">
              {{ truncateText(signal.signal_reason, 60) }}
            </div>
            <div class="signal-time">
              {{ formatTime(signal.computed_at) }}
            </div>
          </div>
        </div>
      </TransitionGroup>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <n-icon size="40" color="var(--n-text-color-3)">
        <SignalIcon />
      </n-icon>
      <span>等待信号...</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { NButton, NTag, NIcon } from 'naive-ui'
import {
  ArrowUp as ArrowUpIcon,
  ArrowDown as ArrowDownIcon,
  Remove as MinusIcon,
  Analytics as SignalIcon,
} from '@vicons/ionicons5'
import { useAlertStore } from '../../stores/alert-store'

// Store
const store = useAlertStore()

// 格式化周期
function formatInterval(interval: string): string {
  const intervalMap: Record<string, string> = {
    '1': '1m',
    '5': '5m',
    '15': '15m',
    '60': '1h',
    '240': '4h',
    'D': '1D',
    'W': '1W',
  }
  return intervalMap[interval] || interval
}

// 格式化时间
function formatTime(timeStr: string): string {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 截断文本
function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

// 生命周期
onMounted(() => {
  // 使用 initialize() 而不是 connectWebSocket()
  // initialize() 会先连接 WebSocket，然后获取数据并订阅信号事件
  store.initialize()
})

onUnmounted(() => {
  // 组件卸载时不关闭 WebSocket，保持全局连接
})
</script>

<style scoped>
.realtime-signals {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--n-color);
  border-radius: 8px;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--n-border-color);
  background: var(--n-color-embedded);
}

.title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
}

.actions {
  display: flex;
  gap: 8px;
}

.signal-stream {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.signal-item {
  display: flex;
  gap: 10px;
  padding: 10px;
  margin-bottom: 8px;
  border-radius: 6px;
  background: var(--n-color-embedded);
  border-left: 3px solid transparent;
  transition: all 0.3s ease;
}

.signal-item.signal-long {
  border-left-color: #18a058;
  background: rgba(24, 160, 88, 0.08);
}

.signal-item.signal-short {
  border-left-color: #d03050;
  background: rgba(208, 48, 80, 0.08);
}

.signal-item.signal-none {
  border-left-color: #909399;
}

.signal-icon {
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
}

.signal-content {
  flex: 1;
  min-width: 0;
}

.signal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.strategy-name {
  font-weight: 600;
  font-size: 13px;
}

.signal-type {
  font-size: 12px;
  font-weight: 500;
}

.signal-long .signal-type {
  color: #18a058;
}

.signal-short .signal-type {
  color: #d03050;
}

.signal-none .signal-type {
  color: #909399;
}

.signal-info {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--n-text-color-3);
  margin-bottom: 4px;
}

.signal-reason {
  font-size: 11px;
  color: var(--n-text-color-2);
  margin-bottom: 4px;
  line-height: 1.4;
}

.signal-time {
  font-size: 11px;
  color: var(--n-text-color-3);
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--n-text-color-3);
  font-size: 13px;
}

/* Transition animations */
.signal-enter-active {
  transition: all 0.3s ease;
}

.signal-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.signal-leave-active {
  transition: all 0.2s ease;
}

.signal-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
