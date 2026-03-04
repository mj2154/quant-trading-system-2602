<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import {
  NDataTable,
  NSpace,
  NSelect,
  NButton,
  NPagination,
  NCard,
  NTag,
  NDropdown,
  NIcon,
  NEmpty,
} from 'naive-ui'
import { useTradingStore } from '../../stores/trading-store'
import OrderStatus from './OrderStatus.vue'
import type { Order, MarketType, OrderStatus as OrderStatusType, OrderSide, OrderFilters } from '../../types/trading-types'

// Simple message handler - can be enhanced later with proper provider
let messageHandler: ((type: 'success' | 'error', text: string) => void) | null = null

// Register message handler from parent (App.vue should provide this)
function showMessage(type: 'success' | 'error', text: string) {
  if (messageHandler) {
    messageHandler(type, text)
  } else {
    // Fallback: use console in development
    if (import.meta.env.DEV) {
      console[type === 'success' ? 'log' : 'error']('[OrderList]', text)
    }
  }
}

// Expose registerMessageHandler for parent to call
import { provide } from 'vue'
provide('registerMessageHandler', (handler: typeof messageHandler) => {
  messageHandler = handler
})

// Store
const tradingStore = useTradingStore()

// State
const marketFilter = ref<MarketType | undefined>(undefined)
const statusFilter = ref<OrderStatusType | undefined>(undefined)
const sideFilter = ref<OrderSide | undefined>(undefined)
const symbolFilter = ref<string | undefined>(undefined)
const currentPage = ref(1)
const pageSize = ref(10)

// Filter options
const marketOptions = [
  { label: '全部市场', value: undefined },
  { label: '合约', value: 'FUTURES' },
  { label: '现货', value: 'SPOT' },
]

const statusOptions = [
  { label: '全部状态', value: undefined },
  { label: '新订单', value: 'NEW' },
  { label: '部分成交', value: 'PARTIALLY_FILLED' },
  { label: '已成交', value: 'FILLED' },
  { label: '已取消', value: 'CANCELED' },
  { label: '已拒绝', value: 'REJECTED' },
  { label: '已过期', value: 'EXPIRED' },
]

const sideOptions = [
  { label: '全部方向', value: undefined },
  { label: '买入', value: 'BUY' },
  { label: '卖出', value: 'SELL' },
]

// Computed
const filteredOrders = computed(() => {
  let result = [...tradingStore.orders]

  if (marketFilter.value) {
    result = result.filter((o) => o.marketType === marketFilter.value)
  }

  if (statusFilter.value) {
    result = result.filter((o) => o.status === statusFilter.value)
  }

  if (sideFilter.value) {
    result = result.filter((o) => o.side === sideFilter.value)
  }

  if (symbolFilter.value) {
    result = result.filter((o) => o.symbol.toLowerCase().includes(symbolFilter.value!.toLowerCase()))
  }

  return result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
})

const paginatedOrders = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredOrders.value.slice(start, end)
})

const totalCount = computed(() => filteredOrders.value.length)

// Table columns
const columns = [
  {
    title: '时间',
    key: 'createdAt',
    width: 180,
    render: (row: Order) => {
      const date = new Date(row.createdAt)
      return date.toLocaleString('zh-CN')
    },
  },
  {
    title: '交易对',
    key: 'symbol',
    width: 120,
  },
  {
    title: '市场',
    key: 'marketType',
    width: 100,
    render: (row: Order) => {
      return h(NTag, { type: row.marketType === 'FUTURES' ? 'warning' : 'info', size: 'small' }, () => row.marketType === 'FUTURES' ? '合约' : '现货')
    },
  },
  {
    title: '方向',
    key: 'side',
    width: 80,
    render: (row: Order) => {
      return h(NTag, { type: row.side === 'BUY' ? 'success' : 'error', size: 'small' }, () => row.side === 'BUY' ? '买入' : '卖出')
    },
  },
  {
    title: '类型',
    key: 'orderType',
    width: 120,
  },
  {
    title: '价格',
    key: 'price',
    width: 120,
    render: (row: Order) => {
      const price = row.data?.price as string | undefined
      return price || '-'
    },
  },
  {
    title: '数量',
    key: 'quantity',
    width: 100,
    render: (row: Order) => {
      const qty = row.data?.quantity as string | undefined
      return qty || '-'
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: (row: Order) => {
      return h(OrderStatus, { status: row.status, side: row.side })
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 100,
    render: (row: Order) => {
      const options = [
        { label: '查看详情', key: 'view' },
        row.status === 'NEW' || row.status === 'PARTIALLY_FILLED'
          ? { label: '取消', key: 'cancel' }
          : null,
      ].filter(Boolean)

      return h(
        NDropdown,
        {
          options: options as any,
          onSelect: (key: string) => handleAction(key, row),
        },
        {
          default: () =>
            h(NButton, { size: 'small', tertiary: true }, () => '操作'),
        }
      )
    },
  },
]

// Methods
async function refresh() {
  const filters: OrderFilters = {}
  if (marketFilter.value) filters.marketType = marketFilter.value
  if (statusFilter.value) filters.status = statusFilter.value
  if (sideFilter.value) filters.side = sideFilter.value

  await tradingStore.fetchOrders(filters)
}

function handleAction(key: string, order: Order) {
  if (key === 'view') {
    tradingStore.setCurrentOrder(order)
  } else if (key === 'cancel') {
    handleCancel(order)
  }
}

async function handleCancel(order: Order) {
  try {
    await tradingStore.cancelOrder(order.clientOrderId)
    showMessage('success', 'Order cancelled successfully')
  } catch (e) {
    showMessage('error', 'Failed to cancel order')
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
}

// Initialize
onMounted(() => {
  refresh()
})
</script>

<template>
  <NCard title="订单列表" size="small">
    <template #header-extra>
      <NButton
        data-testid="refresh-button"
        size="small"
        @click="refresh"
      >
        刷新
      </NButton>
    </template>

    <!-- Filters -->
    <NSpace vertical :size="12" style="margin-bottom: 16px">
      <NSpace>
        <NSelect
          v-model:value="marketFilter"
          :options="marketOptions"
          placeholder="市场"
          style="width: 140px"
          clearable
          data-testid="market-filter"
        />
        <NSelect
          v-model:value="statusFilter"
          :options="statusOptions"
          placeholder="状态"
          style="width: 140px"
          clearable
          data-testid="status-filter"
        />
        <NSelect
          v-model:value="sideFilter"
          :options="sideOptions"
          placeholder="方向"
          style="width: 120px"
          clearable
          data-testid="side-filter"
        />
      </NSpace>
    </NSpace>

    <!-- Table -->
    <NDataTable
      :columns="columns"
      :data="paginatedOrders"
      :loading="tradingStore.isLoading"
      :max-height="500"
      :bordered="false"
      :row-key="(row: Order) => row.clientOrderId"
      size="small"
      :theme-overrides="{
        thColor: 'rgba(15, 23, 42, 0.8)',
        tdColor: 'transparent',
        tdColorHover: 'rgba(245, 158, 11, 0.08)',
        borderColor: 'rgba(245, 158, 11, 0.15)',
        thTextColor: '#94A3B8',
        tdTextColor: '#F8FAFC',
      }"
    />

    <!-- Empty state -->
    <NEmpty
      v-if="filteredOrders.length === 0 && !tradingStore.isLoading"
      description="暂无订单"
      style="margin-top: 20px"
    />

    <!-- Pagination -->
    <div v-if="totalCount > 0" style="margin-top: 16px; display: flex; justify-content: flex-end">
      <NPagination
        v-model:page="currentPage"
        :page-size="pageSize"
        :item-count="totalCount"
        @update:page="handlePageChange"
      />
    </div>
  </NCard>
</template>

<style scoped>
/* Card styling override for dark theme */
:deep(.n-card) {
  background: transparent !important;
  border: none !important;
}

:deep(.n-card-header) {
  padding: 16px 0 12px 0;
}

:deep(.n-card-header__main) {
  font-family: 'Exo 2', 'Orbitron', sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #F59E0B;
  text-shadow: 0 0 10px rgba(245, 158, 11, 0.3);
  letter-spacing: 0.5px;
}

:deep(.n-card-header__extra) {
  padding: 12px 0;
}

/* Select filter styling */
:deep(.n-base-selection) {
  --n-border: 1px solid rgba(245, 158, 11, 0.2);
  --n-border-hover: 1px solid rgba(245, 158, 11, 0.4);
  --n-color: rgba(15, 23, 42, 0.8);
}

:deep(.n-base-selection-label) {
  color: #94A3B8;
}

/* Button styling */
:deep(.n-button) {
  transition: all 0.2s ease;
}

:deep(.n-button:hover) {
  border-color: rgba(245, 158, 11, 0.4);
}

/* Pagination styling */
:deep(.n-pagination) {
  --n-button-color: rgba(15, 23, 42, 0.8);
  --n-button-border: 1px solid rgba(245, 158, 11, 0.2);
  --n-button-color-hover: rgba(245, 158, 11, 0.15);
  --n-button-color-active: #F59E0B;
  --n-button-text-color-active: #0F172A;
}

/* Empty state */
:deep(.n-empty) {
  --n-color: transparent;
}

:deep(.n-empty__description) {
  color: #64748B;
}
</style>
