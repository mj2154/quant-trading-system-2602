<script setup lang="ts">
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import type { OrderStatus as OrderStatusType, OrderSide } from '../../types/trading-types'

interface Props {
  status: OrderStatusType
  side?: OrderSide
  size?: 'small' | 'medium' | 'large'
}

const props = withDefaults(defineProps<Props>(), {
  side: undefined,
  size: 'small',
})

const statusConfig = computed(() => {
  const configMap: Record<OrderStatusType, { text: string; type: 'info' | 'warning' | 'success' | 'error' | 'default' }> = {
    NEW: { text: '新订单', type: 'info' },
    PARTIALLY_FILLED: { text: '部分成交', type: 'warning' },
    FILLED: { text: '已成交', type: 'success' },
    CANCELED: { text: '已取消', type: 'default' },
    PENDING_CANCEL: { text: '取消中', type: 'warning' },
    REJECTED: { text: '已拒绝', type: 'error' },
    EXPIRED: { text: '已过期', type: 'default' },
  }
  return configMap[props.status] || { text: props.status, type: 'default' as const }
})

const tagType = computed(() => statusConfig.value.type)
const displayText = computed(() => statusConfig.value.text)
</script>

<template>
  <NTag :type="tagType" :size="size" :bordered="false" class="order-status-tag">
    {{ displayText }}
  </NTag>
</template>

<style scoped>
.order-status-tag {
  font-weight: 500;
  font-size: 11px;
  letter-spacing: 0.3px;
}
</style>
