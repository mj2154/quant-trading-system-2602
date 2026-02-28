<template>
  <div class="realtime-signals" role="log" aria-label="实时交易信号流" aria-live="polite">
    <!-- 信号列表 -->
    <div v-if="store.realtimeAlertSignals.length > 0" class="signal-stream" role="list">
      <TransitionGroup name="signal">
        <div
          v-for="signal in store.realtimeAlertSignals"
          :key="signal.alert_id"
          class="signal-item"
          role="listitem"
          :aria-label="`${signal.strategy_name} - ${signal.signal_value === true ? '建仓信号' : signal.signal_value === false ? '清仓信号' : '观望'}`"
          :class="{
            'signal-long': signal.signal_value === true,
            'signal-short': signal.signal_value === false,
            'signal-none': signal.signal_value === null,
          }"
        >
          <!-- 发光指示条 -->
          <div class="glow-bar" :class="{
            'glow-long': signal.signal_value === true,
            'glow-short': signal.signal_value === false,
          }"></div>

          <div class="signal-icon">
            <div class="icon-wrapper" :class="{
              'icon-long': signal.signal_value === true,
              'icon-short': signal.signal_value === false,
            }">
              <n-icon v-if="signal.signal_value === true" size="16">
                <ArrowUpIcon />
              </n-icon>
              <n-icon v-else-if="signal.signal_value === false" size="16">
                <ArrowDownIcon />
              </n-icon>
              <n-icon v-else size="16">
                <MinusIcon />
              </n-icon>
            </div>
          </div>

          <div class="signal-content">
            <div class="signal-header">
              <span class="strategy-name">{{ signal.strategy_name }}</span>
              <span class="signal-type" :class="{
                'type-long': signal.signal_value === true,
                'type-short': signal.signal_value === false,
              }">
                {{ signal.signal_value === true ? '建仓' : signal.signal_value === false ? '清仓' : '观望' }}
              </span>
            </div>
            <div class="signal-info">
              <span class="symbol-badge">{{ formatSymbol(signal.symbol) }}</span>
              <span class="interval-badge">{{ formatInterval(signal.interval) }}</span>
            </div>
            <div v-if="signal.signal_reason" class="signal-reason">
              {{ truncateText(signal.signal_reason, 50) }}
            </div>
            <div class="signal-time">
              <span class="time-icon">◷</span>
              {{ formatTime(signal.computed_at) }}
            </div>
          </div>
        </div>
      </TransitionGroup>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state" role="status" aria-label="等待信号触发">
      <div class="empty-illustration" aria-hidden="true">
        <div class="radar-sweep"></div>
        <n-icon size="32" color="rgba(245, 158, 11, 0.3)">
          <SignalIcon />
        </n-icon>
      </div>
      <span class="empty-text">扫描市场中...</span>
      <span class="empty-subtext">等待信号触发</span>
    </div>

    <!-- 清空按钮 -->
    <div v-if="store.realtimeAlertSignals.length > 0" class="stream-footer" role="toolbar" aria-label="信号流操作">
      <n-button size="tiny" quaternary @click="store.clearRealtimeAlertSignals" aria-label="清空信号记录">
        <template #icon>
          <n-icon><TrashOutline /></n-icon>
        </template>
        清空记录
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { NButton, NIcon } from 'naive-ui'
import {
  ArrowUp as ArrowUpIcon,
  ArrowDown as ArrowDownIcon,
  Remove as MinusIcon,
  Analytics as SignalIcon,
  TrashOutline,
} from '@vicons/ionicons5'
import { useAlertStore } from '../../stores/alert-store'

// Store
const store = useAlertStore()

// 格式化交易对
function formatSymbol(symbol: string): string {
  const prefix = 'BINANCE:'
  if (symbol.startsWith(prefix)) {
    return symbol.slice(prefix.length).replace('USDT', '')
  }
  return symbol
}

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
  background: transparent;
  overflow: hidden;
}

.signal-stream {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  scrollbar-width: thin;
  scrollbar-color: rgba(245, 158, 11, 0.3) transparent;
}

.signal-stream::-webkit-scrollbar {
  width: 4px;
}

.signal-stream::-webkit-scrollbar-track {
  background: transparent;
}

.signal-stream::-webkit-scrollbar-thumb {
  background: rgba(245, 158, 11, 0.3);
  border-radius: 2px;
}

.signal-item {
  position: relative;
  display: flex;
  gap: 12px;
  padding: 12px;
  margin-bottom: 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.08);
  overflow: hidden;
  /* 使用 transform 和 opacity 进行 GPU 加速 */
  transform: translateZ(0);
  will-change: transform, opacity;
  transition: transform 0.2s ease-out, opacity 0.2s ease-out, background 0.2s ease-out;
}

.signal-item:hover {
  background: rgba(255, 255, 255, 0.05);
  transform: translateX(2px) translateZ(0);
}

/* 发光指示条 */
.glow-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  /* 使用 opacity 替代 background 动画 */
  opacity: 1;
  transition: opacity 0.2s ease-out;
}

.glow-bar.glow-long {
  background: linear-gradient(180deg, #10B981 0%, #059669 100%);
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.5), 0 0 24px rgba(16, 185, 129, 0.2);
}

.glow-bar.glow-short {
  background: linear-gradient(180deg, #EF4444 0%, #DC2626 100%);
  box-shadow: 0 0 12px rgba(239, 68, 68, 0.5), 0 0 24px rgba(239, 68, 68, 0.2);
}

/* 信号入场动画 - 使用 GPU 加速属性 */
.signal-item.signal-long {
  animation: slide-in-long 0.3s ease-out;
}

.signal-item.signal-short {
  animation: slide-in-short 0.3s ease-out;
}

@keyframes slide-in-long {
  0% {
    opacity: 0;
    transform: translateX(-20px) translateZ(0);
  }
  100% {
    opacity: 1;
    transform: translateX(0) translateZ(0);
  }
}

@keyframes slide-in-short {
  0% {
    opacity: 0;
    transform: translateX(-20px) translateZ(0);
  }
  100% {
    opacity: 1;
    transform: translateX(0) translateZ(0);
  }
}

.signal-icon {
  display: flex;
  align-items: center;
  padding-top: 2px;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  transition: all 0.2s ease-out;
}

.icon-wrapper.icon-long {
  background: rgba(16, 185, 129, 0.15);
  color: #10B981;
}

.icon-wrapper.icon-short {
  background: rgba(239, 68, 68, 0.15);
  color: #EF4444;
}

.signal-content {
  flex: 1;
  min-width: 0;
}

.signal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.strategy-name {
  font-weight: 600;
  font-size: 13px;
  color: #F8FAFC;
}

.signal-type {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.signal-type.type-long {
  background: rgba(16, 185, 129, 0.15);
  color: #10B981;
}

.signal-type.type-short {
  background: rgba(239, 68, 68, 0.15);
  color: #EF4444;
}

.signal-info {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}

.symbol-badge {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  background: rgba(245, 158, 11, 0.12);
  color: #F59E0B;
  border-radius: 6px;
}

.interval-badge {
  font-size: 11px;
  padding: 2px 6px;
  background: rgba(255, 255, 255, 0.06);
  color: #94A3B8;
  border-radius: 6px;
}

.signal-reason {
  font-size: 11px;
  color: #64748B;
  margin-bottom: 6px;
  line-height: 1.4;
}

.signal-time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: #475569;
}

.time-icon {
  font-size: 10px;
}

/* 空状态 */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 20px;
}

.empty-illustration {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  margin-bottom: 12px;
}

.radar-sweep {
  position: absolute;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    rgba(245, 158, 11, 0.1) 60deg,
    rgba(245, 158, 11, 0.2) 120deg,
    transparent 180deg
  );
  animation: radar-sweep 3s linear infinite;
}

@keyframes radar-sweep {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.empty-text {
  font-size: 14px;
  color: #94A3B8;
  font-weight: 500;
}

.empty-subtext {
  font-size: 11px;
  color: #475569;
}

/* 底部操作栏 */
.stream-footer {
  display: flex;
  justify-content: center;
  padding: 10px;
  border-top: 1px solid rgba(245, 158, 11, 0.08);
  background: rgba(245, 158, 11, 0.02);
}

/* Transition animations - 使用 GPU 加速 */
.signal-enter-active {
  transition: opacity 0.3s ease-out, transform 0.3s ease-out;
}

.signal-enter-from {
  opacity: 0;
  transform: translateX(-20px) translateZ(0);
}

.signal-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.signal-leave-to {
  opacity: 0;
  transform: translateX(20px) translateZ(0);
}

/* 键盘导航焦点样式 */
.signal-item:focus-visible {
  outline: 2px solid #F59E0B;
  outline-offset: 2px;
}

/* 减少动画支持 - 禁用所有动画 */
@media (prefers-reduced-motion: reduce) {
  .signal-item,
  .signal-item.signal-long,
  .signal-item.signal-short,
  .glow-bar,
  .icon-wrapper,
  .radar-sweep,
  .signal-enter-active,
  .signal-leave-active {
    animation: none !important;
    transition: none !important;
  }

  .signal-item {
    opacity: 1;
    transform: none !important;
  }

  .signal-enter-from,
  .signal-leave-to {
    opacity: 0;
    transform: none;
  }
}
</style>
