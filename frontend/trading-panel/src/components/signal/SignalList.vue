<template>
  <div class="signal-list">
    <!-- 筛选工具栏 -->
    <div class="toolbar">
      <n-space :size="12">
        <n-select
          v-model:value="filterSymbol"
          placeholder="交易对"
          clearable
          style="width: 150px"
          :options="symbolOptions"
          @update:value="handleFilterChange"
        />
        <n-select
          v-model:value="filterInterval"
          placeholder="周期"
          clearable
          style="width: 100px"
          :options="intervalOptions"
          @update:value="handleFilterChange"
        />
        <n-select
          v-model:value="filterSignal"
          placeholder="信号"
          clearable
          style="width: 100px"
          :options="signalOptions"
          @update:value="handleFilterChange"
        />
        <n-button @click="handleClearFilter">清除筛选</n-button>
      </n-space>
      <n-button @click="handleRefresh">
        <template #icon>
          <n-icon><RefreshOutline /></n-icon>
        </template>
        刷新
      </n-button>
    </div>

    <!-- 加载状态 -->
    <div v-if="store.alertSignalsLoading && store.alertSignals.length === 0" class="loading">
      <n-spin size="medium" />
      <span>加载中...</span>
    </div>

    <!-- 信号列表 -->
    <div v-else class="signal-items">
      <n-card
        v-for="signal in store.alertSignals"
        :key="signal.id"
        class="signal-card"
        size="small"
        hoverable
        @click="handleSelect(signal)"
      >
        <template #header>
          <div class="card-header">
            <span class="strategy-name">{{ signal.strategy_name }}</span>
            <n-tag
              v-if="signal.signal_value !== null"
              :type="signal.signal_value ? 'success' : 'error'"
              size="small"
            >
              {{ signal.signal_value ? '做多' : '做空' }}
            </n-tag>
            <n-tag v-else type="default" size="small">无信号</n-tag>
          </div>
        </template>

        <div class="card-content">
          <div class="info-row">
            <span class="label">{{ signal.symbol }}</span>
            <span class="value">{{ formatInterval(signal.interval) }}</span>
          </div>
          <div v-if="signal.signal_reason" class="signal-reason">
            {{ signal.signal_reason }}
          </div>
          <div class="info-row time">
            <span class="label">时间:</span>
            <span class="value">{{ formatTime(signal.computed_at) }}</span>
          </div>
        </div>
      </n-card>
    </div>

    <!-- 空状态 -->
    <n-empty
      v-if="!store.alertSignalsLoading && store.alertSignals.length === 0"
      description="暂无信号"
      class="empty-state"
    />

    <!-- 分页 -->
    <div v-if="store.alertSignals.length > 0" class="pagination">
      <n-pagination
        v-model:page="currentPage"
        :page-count="totalPages"
        :page-slot="5"
        @update:page="handlePageChange"
      />
    </div>

    <!-- 详情对话框 -->
    <n-modal v-model:show="showDetail" preset="card" title="信号详情" style="width: 600px">
      <n-descriptions v-if="selectedSignal" :column="2" label-placement="top" bordered>
        <n-descriptions-item label="告警ID">{{ selectedSignal.alert_id }}</n-descriptions-item>
        <n-descriptions-item label="策略名称">{{ selectedSignal.strategy_name }}</n-descriptions-item>
        <n-descriptions-item label="交易对">{{ selectedSignal.symbol }}</n-descriptions-item>
        <n-descriptions-item label="周期">{{ formatInterval(selectedSignal.interval) }}</n-descriptions-item>
        <n-descriptions-item label="信号值">
          <n-tag v-if="selectedSignal.signal_value !== null" :type="selectedSignal.signal_value ? 'success' : 'error'">
            {{ selectedSignal.signal_value ? '做多' : '做空' }}
          </n-tag>
          <span v-else>无信号</span>
        </n-descriptions-item>
        <n-descriptions-item label="触发类型">{{ selectedSignal.trigger_type || '-' }}</n-descriptions-item>
        <n-descriptions-item label="计算时间" :span="2">{{ formatTime(selectedSignal.computed_at) }}</n-descriptions-item>
        <n-descriptions-item label="信号原因" :span="2">{{ selectedSignal.signal_reason || '-' }}</n-descriptions-item>
        <n-descriptions-item v-if="selectedSignal.source_subscription_key" label="订阅键" :span="2">
          {{ selectedSignal.source_subscription_key }}
        </n-descriptions-item>
        <n-descriptions-item v-if="selectedSignal.metadata" label="元数据" :span="2">
          <pre class="metadata-json">{{ JSON.stringify(selectedSignal.metadata, null, 2) }}</pre>
        </n-descriptions-item>
      </n-descriptions>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  NCard,
  NButton,
  NSpace,
  NSelect,
  NIcon,
  NSpin,
  NEmpty,
  NPagination,
  NTag,
  NModal,
  NDescriptions,
  NDescriptionsItem,
} from 'naive-ui'
import { RefreshOutline } from '@vicons/ionicons5'
import { useAlertStore, type SignalRecord } from '../../stores/alert-store'

// 组件事件
const emit = defineEmits<{
  (e: 'select', signal: SignalRecord): void
}>()

// Store
const store = useAlertStore()

// 筛选状态
const filterSymbol = ref<string | null>(null)
const filterInterval = ref<string | null>(null)
const filterSignal = ref<number | null>(null)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)

// 详情
const showDetail = ref(false)
const selectedSignal = ref<SignalRecord | null>(null)

// 选项
const symbolOptions = [
  { label: 'BTC/USDT', value: 'BINANCE:BTCUSDT' },
  { label: 'ETH/USDT', value: 'BINANCE:ETHUSDT' },
  { label: 'BNB/USDT', value: 'BINANCE:BNBUSDT' },
  { label: 'SOL/USDT', value: 'BINANCE:SOLUSDT' },
]

const intervalOptions = [
  { label: '1分钟', value: '1' },
  { label: '5分钟', value: '5' },
  { label: '15分钟', value: '15' },
  { label: '1小时', value: '60' },
  { label: '4小时', value: '240' },
]

const signalOptions = [
  { label: '做多', value: 1 },
  { label: '做空', value: 0 },
]

// 计算总页数
const totalPages = computed(() => {
  const total = store.alertSignalQueryParams.page_size || 20
  return Math.ceil(store.alertSignals.length / total)
})

// 格式化周期
function formatInterval(interval: string): string {
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

// 格式化时间
function formatTime(timeStr: string): string {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// 处理筛选变化
function handleFilterChange() {
  store.setAlertSignalFilter({
    symbol: filterSymbol.value || undefined,
    interval: filterInterval.value || undefined,
    signal_value: filterSignal.value !== null ? filterSignal.value === 1 : undefined,
    page: 1,
  })
  store.fetchAlertSignals()
}

// 清除筛选
function handleClearFilter() {
  filterSymbol.value = null
  filterInterval.value = null
  filterSignal.value = null
  store.clearAlertSignalFilter()
  store.fetchAlertSignals()
}

// 处理刷新
async function handleRefresh() {
  await store.fetchAlertSignals()
}

// 处理分页
function handlePageChange(page: number) {
  currentPage.value = page
  store.setAlertSignalFilter({ page })
  store.fetchAlertSignals()
}

// 处理选择
function handleSelect(signal: SignalRecord) {
  selectedSignal.value = signal
  showDetail.value = true
  emit('select', signal)
}

// 生命周期
onMounted(() => {
  if (store.alertSignals.length === 0) {
    store.fetchAlertSignals()
  }
})
</script>

<style scoped>
.signal-list {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: var(--n-text-color-3);
}

.signal-items {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.signal-card {
  cursor: pointer;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strategy-name {
  font-weight: 600;
  font-size: 14px;
  flex: 1;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.info-row .label {
  color: var(--n-text-color-3);
}

.info-row .value {
  color: var(--n-text-color-1);
}

.signal-reason {
  font-size: 12px;
  color: var(--n-text-color-2);
  margin: 4px 0;
  padding: 4px;
  background: var(--n-color-embedded);
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}

.info-row.time {
  color: var(--n-text-color-3);
}

.empty-state {
  padding: 40px;
}

.pagination {
  display: flex;
  justify-content: center;
  padding: 16px 0;
  border-top: 1px solid var(--n-border-color);
  margin-top: 16px;
}

.metadata-json {
  background: var(--n-color-embedded);
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 200px;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
