<template>
  <div class="alert-dashboard">
    <!-- 统计栏 -->
    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-value">{{ store.alerts.length }}</span>
        <span class="stat-label">总告警</span>
      </div>
      <div class="stat-item active">
        <span class="stat-value">{{ activeAlertCount }}</span>
        <span class="stat-label">启用中</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ store.realtimeAlertSignals.length }}</span>
        <span class="stat-label">今日信号</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">{{ todaySignalCount }}</span>
        <span class="stat-label">今日触发</span>
      </div>

      <!-- 告警设置 -->
      <div class="settings-group">
        <n-tooltip trigger="hover">
          <template #trigger>
            <div class="setting-item" :class="{ active: alertSettings.popupEnabled }" @click="alertSettings.popupEnabled = !alertSettings.popupEnabled">
              <n-icon size="16">
                <AlertCircleOutline v-if="alertSettings.popupEnabled" />
                <AlertCircleOutline v-else />
              </n-icon>
              <span class="setting-label">弹窗</span>
              <n-switch v-model:value="alertSettings.popupEnabled" size="small" />
            </div>
          </template>
          {{ alertSettings.popupEnabled ? '弹窗已启用' : '弹窗已禁用' }}
        </n-tooltip>

        <n-tooltip trigger="hover">
          <template #trigger>
            <div class="setting-item" :class="{ active: alertSettings.soundEnabled }" @click="alertSettings.soundEnabled = !alertSettings.soundEnabled">
              <n-icon size="16">
                <VolumeHighOutline v-if="alertSettings.soundEnabled" />
                <VolumeMuteOutline v-else />
              </n-icon>
              <span class="setting-label">声音</span>
              <n-switch v-model:value="alertSettings.soundEnabled" size="small" />
            </div>
          </template>
          {{ alertSettings.soundEnabled ? '声音已启用' : '声音已禁用' }}
        </n-tooltip>

        <n-tooltip trigger="hover">
          <template #trigger>
            <div class="setting-item duration" @click="cycleDuration">
              <n-icon size="16">
                <TimeOutline />
              </n-icon>
              <span class="setting-label">{{ soundDurationText }}</span>
            </div>
          </template>
          点击切换声音时长
        </n-tooltip>

        <n-tooltip trigger="hover">
          <template #trigger>
            <div class="setting-item sound-type" @click="cycleSoundType">
              <n-icon size="16">
                <MusicalNotesOutline />
              </n-icon>
              <span class="setting-label">{{ soundTypeText }}</span>
            </div>
          </template>
          点击切换音效类型
        </n-tooltip>
      </div>
    </div>

    <!-- 主从布局 -->
    <div class="dashboard-layout">
      <!-- 左侧：告警配置区域 -->
      <div class="main-panel">
        <!-- 面包屑导航 -->
        <div class="breadcrumb">
          <span class="breadcrumb-item" :class="{ active: activeMode === 'list' }" @click="handleBackToList">
            告警列表
          </span>
          <span v-if="activeMode === 'form'" class="breadcrumb-separator">/</span>
          <span v-if="activeMode === 'form'" class="breadcrumb-item active">
            {{ isEditMode ? '编辑告警' : '新建告警' }}
          </span>
        </div>

        <!-- 告警列表 -->
        <div v-show="activeMode === 'list'" class="panel-content">
          <AlertConfigList
            @select="handleSelectAlert"
            @create="handleCreate"
            @edit="handleEditAlert"
          />
        </div>

        <!-- 告警表单 -->
        <div v-if="activeMode === 'form'" class="panel-content">
          <AlertConfigForm
            :alert="editingAlert"
            @submit="handleSubmitForm"
            @cancel="handleCancelForm"
          />
        </div>
      </div>

      <!-- 右侧：实时告警流 -->
      <div class="sidebar-panel">
        <div class="sidebar-header">
          <div class="sidebar-title">
            <span class="pulse-dot" :class="{ connected: store.wsConnected }"></span>
            实时信号
          </div>
          <div class="connection-status">
            <span class="status-dot" :class="store.wsConnected ? 'online' : 'offline'"></span>
            {{ store.wsConnected ? '已连接' : '未连接' }}
          </div>
        </div>
        <RealtimeAlerts />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMessage, NIcon, NSwitch, NTooltip } from 'naive-ui'
import {
  AlertCircleOutline,
  VolumeHighOutline,
  VolumeMuteOutline,
  TimeOutline,
  MusicalNotesOutline,
} from '@vicons/ionicons5'
import AlertConfigList from '../components/alert/AlertConfigList.vue'
import AlertConfigForm from '../components/alert/AlertConfigForm.vue'
import RealtimeAlerts from '../components/alert/RealtimeAlerts.vue'
import {
  useAlertStore,
  type AlertConfig,
  type AlertConfigCreate,
  type AlertConfigUpdate,
} from '../stores/alert-store'
import { useAlertSettings, SOUND_TYPE_NAMES, type SoundType } from '../composables/useAlertSettings'

// Store
const store = useAlertStore()
const message = useMessage()

// 告警设置
const alertSettings = useAlertSettings().settings

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

// 循环切换声音时长
function cycleDuration() {
  const durations = [5, 15, 30, 60]
  const currentIndex = durations.indexOf(alertSettings.value.soundDuration)
  const nextIndex = (currentIndex + 1) % durations.length
  alertSettings.value.soundDuration = durations[nextIndex]
}

// 循环切换音效类型
function cycleSoundType() {
  const types: SoundType[] = ['beep', 'ding', 'alert']
  const currentIndex = types.indexOf(alertSettings.value.soundType)
  const nextIndex = (currentIndex + 1) % types.length
  alertSettings.value.soundType = types[nextIndex]
}

// 状态
const activeMode = ref<'list' | 'form'>('list')
const editingAlert = ref<AlertConfig | null>(null)

// 计算属性
const showForm = computed(() => editingAlert.value !== null || activeMode.value === 'form')
const isEditMode = computed(() => !!editingAlert.value)
const soundDurationText = computed(() => {
  const duration = alertSettings.value.soundDuration
  return duration >= 60 ? '1分钟' : `${duration}秒`
})
const soundTypeText = computed(() => {
  return SOUND_TYPE_NAMES[alertSettings.value.soundType]
})
const activeAlertCount = computed(() => store.alerts.filter(a => a.is_enabled).length)
const todaySignalCount = computed(() => {
  const today = new Date().toDateString()
  return store.alertSignals.filter(s => new Date(s.computed_at).toDateString() === today).length
})

// 处理返回列表
function handleBackToList() {
  if (activeMode.value === 'form') {
    handleCancelForm()
  }
}

// 处理选择告警
function handleSelectAlert(alert: AlertConfig) {
  console.log('Selected alert:', alert)
}

// 处理创建
function handleCreate() {
  editingAlert.value = null
  activeMode.value = 'form'
}

// 处理编辑
function handleEditAlert(alert: AlertConfig) {
  editingAlert.value = alert
  activeMode.value = 'form'
}

// 处理表单提交
async function handleSubmitForm(data: AlertConfig) {
  let success = false

  if (editingAlert.value) {
    // 编辑模式
    const updateData: AlertConfigUpdate = {
      name: data.name,
      description: data.description ?? undefined,
      trigger_type: data.trigger_type,
      params: data.params ?? undefined,
      symbol: data.symbol,
      interval: data.interval,
      is_enabled: data.is_enabled,
      strategy_type: data.strategy_type,
    }
    const result = await store.updateAlert(editingAlert.value.id, updateData)
    success = !!result
    if (success) {
      message.success('告警更新成功')
    } else {
      message.error(store.alertsError || '更新失败')
    }
  } else {
    // 创建模式
    const createData: AlertConfigCreate = {
      name: data.name,
      description: data.description ?? undefined,
      trigger_type: data.trigger_type,
      params: data.params ?? undefined,
      symbol: data.symbol,
      interval: data.interval,
      is_enabled: data.is_enabled,
      strategy_type: data.strategy_type,
    }
    const result = await store.createAlert(createData)
    success = !!result
    if (success) {
      message.success('告警创建成功')
    } else {
      message.error(store.alertsError || '创建失败')
    }
  }

  if (success) {
    handleCancelForm()
  }
}

// 处理取消表单
function handleCancelForm() {
  editingAlert.value = null
  activeMode.value = 'list'
}
</script>

<style scoped>
.alert-dashboard {
  height: 100%;
  padding: 16px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 统计栏 */
.stats-bar {
  display: flex;
  gap: 12px;
  padding: 14px 18px;
  background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.08);
  transition: all 0.2s ease-out;
}

.stat-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(245, 158, 11, 0.2);
}

.stat-item.active {
  background: rgba(16, 185, 129, 0.1);
  border-color: rgba(16, 185, 129, 0.25);
}

.stat-item.active .stat-value {
  color: #10B981;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  font-family: 'Fira Code', 'SF Mono', monospace;
  color: #F8FAFC;
  line-height: 1;
}

.stat-label {
  font-size: 11px;
  font-weight: 500;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 告警设置区域 */
.settings-group {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-left: 16px;
  margin-left: auto;
  border-left: 1px solid rgba(148, 163, 184, 0.15);
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(148, 163, 184, 0.08);
  cursor: pointer;
  transition: all 0.2s ease;
  color: #64748B;
}

.setting-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(245, 158, 11, 0.3);
}

.setting-item.active {
  color: #F59E0B;
  border-color: rgba(245, 158, 11, 0.3);
  background: rgba(245, 158, 11, 0.1);
}

.setting-item.duration {
  min-width: 70px;
}

.setting-item.sound-type {
  min-width: 80px;
}

.setting-label {
  font-size: 12px;
  font-weight: 500;
}

.dashboard-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.main-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #1E293B;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.1);
}

/* 面包屑导航 */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  background: rgba(15, 23, 42, 0.5);
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
}

.breadcrumb-item {
  font-size: 13px;
  color: #64748B;
  cursor: pointer;
  transition: color 0.2s ease;
}

.breadcrumb-item:hover {
  color: #F59E0B;
}

.breadcrumb-item.active {
  color: #F8FAFC;
  font-weight: 500;
  cursor: default;
}

.breadcrumb-item.active:hover {
  color: #F8FAFC;
}

.breadcrumb-separator {
  color: #475569;
  font-size: 12px;
}

.sidebar-panel {
  width: 380px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid rgba(245, 158, 11, 0.15);
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.05);
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(245, 158, 11, 0.1);
  background: rgba(245, 158, 11, 0.03);
}

.sidebar-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 14px;
  color: #F8FAFC;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(245, 158, 11, 0.3);
  transition: all 0.3s ease;
}

.pulse-dot.connected {
  background: #10B981;
  box-shadow: 0 0 8px #10B981, 0 0 16px rgba(16, 185, 129, 0.3);
  animation: pulse-glow 2s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 0 6px #10B981, 0 0 12px rgba(16, 185, 129, 0.2);
  }
  50% {
    box-shadow: 0 0 12px #10B981, 0 0 24px rgba(16, 185, 129, 0.4);
  }
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #64748B;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.status-dot.online {
  background: #10B981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.6);
}

.status-dot.offline {
  background: #EF4444;
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.6);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* 响应式布局 */
@media (max-width: 1200px) {
  .sidebar-panel {
    width: 320px;
  }

  .stats-bar {
    flex-wrap: wrap;
  }

  .stat-item {
    min-width: calc(50% - 6px);
  }
}

@media (max-width: 900px) {
  .dashboard-layout {
    flex-direction: column;
  }

  .sidebar-panel {
    width: 100%;
    height: 320px;
  }

  .stats-bar {
    flex-wrap: wrap;
  }

  .stat-item {
    min-width: calc(50% - 6px);
  }
}

@media (max-width: 480px) {
  .stat-item {
    min-width: 100%;
  }
}

/* 减少动画支持 */
@media (prefers-reduced-motion: reduce) {
  .stat-item,
  .pulse-dot,
  .status-dot {
    transition: none;
    animation: none;
  }

  .pulse-dot.connected {
    box-shadow: 0 0 8px #10B981;
  }
}
</style>
