<template>
  <!-- 全局告警处理器 - 始终运行在后台，处理声音和弹窗 -->
  <div class="global-alert-handler" style="display: none;"></div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAlertStore } from '../stores/alert-store'
import { useAlertSettings, playAlertSound } from '../composables/useAlertSettings'
import { useNotification } from 'naive-ui'
import type { SignalRecord } from '../stores/alert-store'

const store = useAlertStore()
const alertSettings = useAlertSettings().settings
const notification = useNotification()

// 格式化交易对
function formatSymbolForDisplay(symbol: string): string {
  const prefix = 'BINANCE:'
  if (symbol.startsWith(prefix)) {
    return symbol.slice(prefix.length).replace('USDT', '')
  }
  return symbol
}

// 格式化周期
function formatIntervalForDisplay(interval: string): string {
  const intervalMap: Record<string, string> = {
    '1': '1分钟',
    '5': '5分钟',
    '15': '15分钟',
    '60': '1小时',
    '240': '4小时',
    'D': '1天',
    'W': '1周',
  }
  return intervalMap[interval] || interval
}

// 处理告警触发 - 全局版本（处理声音和弹窗）
function handleGlobalAlert(signal: SignalRecord) {
  const signalType = signal.signal_value === true ? '建仓' : signal.signal_value === false ? '清仓' : '观望'

  // 播放声音
  if (alertSettings.value.soundEnabled) {
    playAlertSound(alertSettings.value.soundDuration, alertSettings.value.soundType)
  }

  // 弹窗通知 - 左下角，不自动消失，最多10个（由 NNotificationProvider 控制）
  if (alertSettings.value.popupEnabled) {
    notification.info({
      title: `交易信号 - ${signal.strategy_name}`,
      content: `${formatSymbolForDisplay(signal.symbol)} ${formatIntervalForDisplay(signal.interval)} ${signalType}`,
      duration: 0, // 不自动消失
    })
  }
}

onMounted(() => {
  // 设置全局告警回调
  store.setSignalCallback(handleGlobalAlert)

  // 初始化 store（连接 WebSocket）
  store.initialize()
})
</script>
