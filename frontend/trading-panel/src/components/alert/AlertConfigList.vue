<template>
  <div class="alert-config-list">
    <!-- 工具栏 -->
    <div class="toolbar">
      <n-button type="primary" @click="handleCreate">
        <template #icon>
          <n-icon><AddOutline /></n-icon>
        </template>
        新建告警
      </n-button>
      <n-button @click="handleRefresh">
        <template #icon>
          <n-icon><ReloadOutline /></n-icon>
        </template>
        刷新
      </n-button>
    </div>

    <!-- 加载状态 -->
    <div v-if="store.alertsLoading && store.alerts.length === 0" class="loading">
      <n-spin size="medium" />
      <span>加载中...</span>
    </div>

    <!-- 错误提示 -->
    <n-alert v-if="store.alertsError" type="error" class="error-alert">
      {{ store.alertsError }}
    </n-alert>

    <!-- 告警列表 -->
    <div v-else-if="store.alerts.length > 0" class="alert-cards">
      <n-card
        v-for="alert in store.alerts"
        :key="alert.id"
        class="alert-card"
        :class="{ disabled: !alert.isEnabled }"
        hoverable
        @click="handleSelect(alert)"
      >
        <template #header>
          <div class="card-header">
            <span class="alert-name">{{ alert.name }}</span>
            <n-tag :type="alert.isEnabled ? 'success' : 'default'" size="small">
              {{ alert.isEnabled ? '启用' : '禁用' }}
            </n-tag>
          </div>
        </template>

        <div class="card-content">
          <!-- 第一行：交易对（突出显示） -->
          <div class="info-row symbol-row">
            <span class="label">交易对</span>
            <span class="value symbol">{{ formatSymbol(alert.symbol) }}</span>
            <span class="interval-tag">{{ formatInterval(alert.interval) }}</span>
          </div>

          <!-- 第二行：触发 + 策略 -->
          <div class="info-row">
            <span class="label">触发</span>
            <span class="value trigger">{{ formatTriggerType(alert.triggerType) }}</span>
          </div>
          <div class="info-row">
            <span class="label">策略</span>
            <span class="value strategy">{{ formatStrategyType(alert.strategyType) }}</span>
          </div>

          <!-- 策略参数 - 完全动态显示 -->
          <div v-if="alert.params && Object.keys(alert.params).length > 0" class="macd-section">
            <!-- 动态分组显示 -->
            <div
              v-for="(params, groupKey) in getParamGroups(alert.params)"
              :key="groupKey"
              class="macd-group"
            >
              <span class="macd-label">{{ getGroupLabel(groupKey as string) }}</span>
              <div class="macd-values">
                <span v-for="(value, paramName) in params" :key="paramName">
                  <small>{{ formatParamName(paramName as string) }}</small>
                  {{ value }}
                </span>
              </div>
            </div>
          </div>

          <!-- 描述 -->
          <div v-if="alert.description" class="info-row desc">
            <span class="label">描述</span>
            <span class="value">{{ alert.description }}</span>
          </div>
        </div>

        <template #action>
          <div class="card-actions">
            <n-button
              size="small"
              :type="alert.isEnabled ? 'warning' : 'success'"
              @click.stop="handleToggle(alert)"
            >
              {{ alert.isEnabled ? '禁用' : '启用' }}
            </n-button>
            <n-button size="small" @click.stop="handleEdit(alert)">编辑</n-button>
            <n-button size="small" type="error" @click.stop="handleDelete(alert)">删除</n-button>
          </div>
        </template>
      </n-card>
    </div>

    <!-- 空状态 -->
    <n-empty v-else description="暂无告警配置" class="empty-state">
      <template #extra>
        <n-button type="primary" @click="handleCreate">创建第一个告警</n-button>
      </template>
    </n-empty>

    <!-- 删除确认对话框 -->
    <n-modal v-model:show="showDeleteModal" preset="dialog" type="warning" title="确认删除">
      <template #default>
        确定要删除告警 "{{ alertToDelete?.name }}" 吗？此操作不可恢复。
      </template>
      <template #action>
        <n-button @click="showDeleteModal = false">取消</n-button>
        <n-button type="error" :loading="deleting" @click="confirmDelete">删除</n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  NButton,
  NCard,
  NTag,
  NIcon,
  NSpin,
  NAlert,
  NEmpty,
  NModal,
  useMessage,
} from 'naive-ui'
import { AddOutline, ReloadOutline } from '@vicons/ionicons5'
import { useAlertStore, type AlertConfig, formatParamName } from '../../stores/alert-store'

// 组件事件
const emit = defineEmits<{
  (e: 'select', alert: AlertConfig): void
  (e: 'create'): void
  (e: 'edit', alert: AlertConfig): void
}>()

// Store
const store = useAlertStore()
const message = useMessage()

// 状态
const showDeleteModal = ref(false)
const alertToDelete = ref<AlertConfig | null>(null)
const deleting = ref(false)

// 格式化交易对
function formatSymbol(symbol: string | undefined): string {
  if (!symbol) return '-'
  const prefix = 'BINANCE:'
  if (symbol.startsWith(prefix)) {
    return symbol.slice(prefix.length).replace('USDT', '/USDT')
  }
  return symbol
}

// 格式化周期
function formatInterval(interval: string | undefined): string {
  if (!interval) return '-'
  const intervalMap: Record<string, string> = {
    '1': '1分钟',
    '5': '5分钟',
    '15': '15分钟',
    '60': '1小时',
    '240': '4小时',
    'D': '日线',
    'W': '周线',
  }
  return intervalMap[interval] || interval
}

// 格式化触发类型
function formatTriggerType(triggerType: string | undefined): string {
  if (!triggerType) return '-'
  const triggerMap: Record<string, string> = {
    'once_only': '仅一次',
    'each_kline': '每根K线',
    'each_kline_close': '每根K线收盘',
    'each_minute': '每分钟',
  }
  return triggerMap[triggerType] || triggerType
}

// 格式化策略类型 - 动态转换
function formatStrategyType(strategyType: string | undefined): string {
  if (!strategyType) return '-'

  // 动态转换：将驼峰命名转换为友好显示
  // 例如：MACDResonanceShortStrategyV1 -> MACD Resonance Short Strategy V1
  const formatted = strategyType
    // 在大写字母前插入空格（但保留连续大写字母）
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
    // V1 保持在一起
    .replace(/([A-Z])(\d+)(?=[A-Z]|$)/g, '$1$2')
    // 1H -> 1 H
    .replace(/(\d+)(?=[A-Z])/g, '$1 ')
    // 替换下划线为空格
    .replace(/_/g, ' ')
    // 合并多个空格
    .replace(/\s+/g, ' ')
    .trim()

  return formatted
}

// 动态获取参数分组（根据前缀分组）
// 例如：{ macd1_fastperiod: 12, macd1_slowperiod: 26, macd2_fastperiod: 5 }
// 转换为：{ 'macd1': { fastperiod: 12, slowperiod: 26 }, 'macd2': { fastperiod: 5 } }
function getParamGroups(params: Record<string, number | boolean> | undefined): Record<string, Record<string, number | boolean>> {
  if (!params) return {}

  const groups: Record<string, Record<string, number | boolean>> = {}

  for (const [key, value] of Object.entries(params)) {
    // 按下划线分割，取第一部分作为组名
    const parts = key.split('_')
    if (parts.length >= 2) {
      const groupKey = parts[0]
      const paramKey = parts.slice(1).join('_')

      if (!groups[groupKey]) {
        groups[groupKey] = {}
      }
      groups[groupKey][paramKey] = value
    } else {
      // 没有前缀的参数单独一组
      if (!groups['other']) {
        groups['other'] = {}
      }
      groups['other'][key] = value
    }
  }

  return groups
}

// 获取分组的显示标签
function getGroupLabel(groupKey: string): string {
  // 将组名转换为友好显示，如 'macd1' -> 'MACD 1'
  const labelMap: Record<string, string> = {
    'macd1': 'MACD 1',
    'macd2': 'MACD 2',
    'macd3': 'MACD 3',
    'macd4': 'MACD 4',
    'other': '其他',
  }
  return labelMap[groupKey] || formatParamName(groupKey)
}

// 处理选择
function handleSelect(alert: AlertConfig) {
  emit('select', alert)
}

// 处理创建
function handleCreate() {
  emit('create')
}

// 处理编辑
function handleEdit(alert: AlertConfig) {
  emit('edit', alert)
}

// 处理刷新
async function handleRefresh() {
  await store.fetchAlerts()
  message.success('刷新成功')
}

// 处理启用/禁用
async function handleToggle(alert: AlertConfig) {
  const success = await store.toggleAlert(alert.id)
  if (success) {
    message.success(alert.isEnabled ? '已禁用' : '已启用')
  } else {
    message.error('操作失败')
  }
}

// 处理删除
function handleDelete(alert: AlertConfig) {
  alertToDelete.value = alert
  showDeleteModal.value = true
}

// 确认删除
async function confirmDelete() {
  if (!alertToDelete.value) return

  deleting.value = true
  const success = await store.deleteAlert(alertToDelete.value.id)
  deleting.value = false

  if (success) {
    message.success('删除成功')
    showDeleteModal.value = false
    alertToDelete.value = null
  } else {
    message.error('删除失败')
  }
}

// 生命周期
onMounted(() => {
  // 使用 initialize() 而不是 fetchAlerts()
  // initialize() 会先连接 WebSocket，连接成功后再获取数据
  store.initialize()
})
</script>

<style scoped>
.alert-config-list {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(245, 158, 11, 0.05);
  border-radius: 10px;
  border: 1px solid rgba(245, 158, 11, 0.1);
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #64748B;
}

.error-alert {
  margin-bottom: 16px;
}

.alert-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
}

.alert-card {
  transition: all 0.2s ease-out;
  border: 1px solid rgba(148, 163, 184, 0.1);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(255, 255, 255, 0.01) 100%);
}

.alert-card:hover {
  border-color: rgba(245, 158, 11, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(245, 158, 11, 0.1);
}

.alert-card.disabled {
  opacity: 0.5;
  border-color: rgba(148, 163, 184, 0.05);
}

.alert-card.disabled:hover {
  transform: none;
  box-shadow: none;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
  margin-bottom: 12px;
}

.alert-name {
  font-weight: 600;
  font-size: 15px;
  color: #F8FAFC;
  letter-spacing: 0.3px;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 信息行布局 - 标签在左，值在右 */
.info-row {
  display: flex;
  align-items: center;
  font-size: 12px;
}

.info-row .label {
  flex-shrink: 0;
  width: 56px;
  padding: 4px 8px;
  background: rgba(148, 163, 184, 0.1);
  color: #64748B;
  border-radius: 4px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-row .value {
  flex: 1;
  padding-left: 10px;
  color: #CBD5E1;
  font-weight: 500;
}

/* 交易对特殊样式 */
.info-row .value.symbol {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #F59E0B;
  font-weight: 600;
}

.info-row .value.symbol::before {
  content: '';
  width: 6px;
  height: 6px;
  background: #F59E0B;
  border-radius: 50%;
  box-shadow: 0 0 6px rgba(245, 158, 11, 0.5);
}

/* 描述信息 */
.info-row.desc {
  align-items: flex-start;
  padding-top: 8px;
  border-top: 1px dashed rgba(148, 163, 184, 0.1);
}

.info-row.desc .label {
  width: auto;
  background: transparent;
  padding: 0;
  color: #475569;
}

.info-row.desc .value {
  padding-left: 8px;
  font-size: 12px;
  color: #64748B;
  line-height: 1.5;
}

/* 交易对单独一行样式 */
.info-row.symbol-row {
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(245, 158, 11, 0.03) 100%);
  border-radius: 8px;
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.info-row.symbol-row .label {
  background: rgba(245, 158, 11, 0.15);
  color: #F59E0B;
}

.info-row.symbol-row .value.symbol {
  font-size: 15px;
  letter-spacing: 1px;
}

.interval-tag {
  margin-left: auto;
  padding: 4px 10px;
  background: rgba(16, 185, 129, 0.1);
  color: #10B981;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
}

/* 触发类型 */
.info-row .value.trigger {
  color: #38BDF8;
}

/* 策略类型 */
.info-row .value.strategy {
  color: #A78BFA;
}

/* MACD 参数区域 */
.macd-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.25);
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.08);
}

.macd-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.macd-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #475569;
}

.macd-values {
  display: flex;
  gap: 6px;
}

.macd-values span {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  font-family: 'Fira Code', 'SF Mono', monospace;
  font-size: 12px;
  color: #CBD5E1;
}

.macd-values span small {
  font-size: 8px;
  color: #64748B;
  text-transform: uppercase;
}

.card-actions {
  display: flex;
  gap: 8px;
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.08);
  margin-top: 8px;
}

.empty-state {
  padding: 40px;
}

/* 键盘导航焦点样式 */
.alert-card:focus-visible {
  outline: 2px solid #F59E0B;
  outline-offset: 2px;
}

/* 减少动画支持 */
@media (prefers-reduced-motion: reduce) {
  .alert-card {
    transition: none;
  }

  .alert-card:hover {
    transform: none;
  }
}
</style>
