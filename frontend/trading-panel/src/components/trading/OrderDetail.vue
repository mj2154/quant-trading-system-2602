<script setup lang="ts">
import { computed } from 'vue'
import { NModal, NCard, NDescriptions, NDescriptionsItem, NButton, NSpace, NDivider } from 'naive-ui'
import OrderStatus from './OrderStatus.vue'
import type { Order } from '../../types/trading-types'

interface Props {
  order: Order
  show?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  show: true,
})

const emit = defineEmits<{
  close: []
}>()

const orderData = computed(() => {
  const data = props.order.data || {}
  return Object.entries(data).map(([key, value]) => ({
    label: key,
    value: String(value),
  }))
})

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString()
}
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    title="Order Details"
    style="width: 600px; max-width: 90vw"
    :mask-closable="true"
    @update:show="emit('close')"
  >
    <NDescriptions label-placement="left" :column="2" bordered>
      <NDescriptionsItem label="Client Order ID">
        {{ order.clientOrderId }}
      </NDescriptionsItem>
      <NDescriptionsItem v-if="order.binanceOrderId" label="Binance Order ID">
        {{ order.binanceOrderId }}
      </NDescriptionsItem>
      <NDescriptionsItem label="Symbol">
        {{ order.symbol }}
      </NDescriptionsItem>
      <NDescriptionsItem label="Market">
        {{ order.marketType }}
      </NDescriptionsItem>
      <NDescriptionsItem label="Side">
        <OrderStatus :status="order.status" :side="order.side" />
      </NDescriptionsItem>
      <NDescriptionsItem label="Type">
        {{ order.orderType }}
      </NDescriptionsItem>
      <NDescriptionsItem label="Status">
        <OrderStatus :status="order.status" :side="order.side" />
      </NDescriptionsItem>
      <NDescriptionsItem label="Created At">
        {{ formatDate(order.createdAt) }}
      </NDescriptionsItem>
      <NDescriptionsItem label="Updated At">
        {{ formatDate(order.updatedAt) }}
      </NDescriptionsItem>
    </NDescriptions>

    <NDivider>Order Data</NDivider>

    <NDescriptions label-placement="left" :column="2" bordered size="small">
      <NDescriptionsItem
        v-for="item in orderData"
        :key="item.label"
        :label="item.label"
      >
        {{ item.value }}
      </NDescriptionsItem>
    </NDescriptions>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="emit('close')">Close</NButton>
      </NSpace>
    </template>
  </NModal>
</template>
