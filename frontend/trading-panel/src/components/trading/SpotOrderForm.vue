<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  NCard,
  NInputNumber,
  NButton,
  NSlider,
  NSpace,
  NText,
  NIcon,
  NSpin,
} from 'naive-ui'
import { useSpotOrder, type SpotOrderType, type SpotTimeInForce } from '../../composables/useSpotOrder'
import { useAccountStore } from '../../stores/account-store'

// Types
type OrderSide = 'BUY' | 'SELL'
type OrderTypeTab = 'LIMIT' | 'MARKET' | 'STOP'

// Quote data from WebSocket
interface QuoteData {
  symbol: string
  lastPrice: string
  priceChange: string
  priceChangePercent: string
  highPrice: string
  lowPrice: string
  volume: string
  quoteVolume: string
}

// Composables
const { createSpotOrder, isLoading, error } = useSpotOrder()
const accountStore = useAccountStore()

// Current price from quotes (WebSocket)
const currentPrice = ref<number>(0)

// WebSocket for quotes
let ws: WebSocket | null = null
const wsConnected = ref(false)

// Connect to WebSocket and fetch quotes once
function connectAndFetchQuote(targetSymbol: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_WS_HOST || 'localhost:8000'
    const url = `${wsProtocol}//${host}/ws/market`

    try {
      ws = new WebSocket(url)

      ws.onopen = () => {
        wsConnected.value = true
        console.log('[SpotOrderForm] WebSocket connected')

        // Send GET_QUOTES request - follow WebSocket protocol v2.0 (same as TV chart)
        ws?.send(JSON.stringify({
          protocolVersion: '2.0',
          type: 'GET_QUOTES',
          requestId: crypto.randomUUID(),
          timestamp: Date.now(),
          data: {
            type: 'quotes',  // Required - maps to GET_QUOTES
            symbols: [`BINANCE:${targetSymbol}`]
          }
        }))
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log('[SpotOrderForm] Received message:', JSON.stringify(message))

          // Handle ACK confirmation
          if (message.type === 'ACK') {
            console.log('[SpotOrderForm] Received ACK, waiting for data...')
            return
          }

          // Handle quotes data response
          if (message.type === 'QUOTES_DATA' && message.data?.quotes?.[0]) {
            const quote = message.data.quotes[0]
            // 正确的字段是 quote.v.lp (TradingView quotes格式)
            currentPrice.value = parseFloat(quote.v?.lp) || 0
            console.log('[SpotOrderForm] Quote price:', currentPrice.value)
            resolve()
          } else if (message.type === 'ERROR') {
            console.error('[SpotOrderForm] Quotes error:', message.data)
            reject(new Error(message.data?.message || 'Failed to get quotes'))
          }
        } catch (e) {
          console.error('[SpotOrderForm] Failed to parse message:', e)
        }
      }

      ws.onerror = (e) => {
        console.error('[SpotOrderForm] WebSocket error:', e)
        reject(e)
      }

      ws.onclose = () => {
        wsConnected.value = false
        console.log('[SpotOrderForm] WebSocket closed')
      }
    } catch (e) {
      reject(e)
    }
  })
}

// Emit for parent notification
const emit = defineEmits<{
  (e: 'order-success', order: unknown): void
  (e: 'order-error', error: string): void
}>()

function showMessage(msg: string, type: 'success' | 'error' = 'success') {
  console.log(`[SpotOrderForm] ${type}: ${msg}`)
  if (type === 'success') {
    emit('order-success', msg)
  } else {
    emit('order-error', msg)
  }
}

// ====== Form State ======
const symbol = ref<string>('BTCUSDT')
const orderTypeTab = ref<OrderTypeTab>('LIMIT')
const orderType = ref<SpotOrderType>('LIMIT')

// Buy side state
const buyPrice = ref<number | undefined>(undefined)
const buyQuantity = ref<number | undefined>(undefined)
const buyInputAmount = ref<number | undefined>(undefined)
const buyStopPrice = ref<number | undefined>(undefined)
const buyTimeInForce = ref<SpotTimeInForce>('GTC')
const buyPercentage = ref(0)

// Sell side state
const sellPrice = ref<number | undefined>(undefined)
const sellQuantity = ref<number | undefined>(undefined)
const sellInputAmount = ref<number | undefined>(undefined)
const sellStopPrice = ref<number | undefined>(undefined)
const sellTimeInForce = ref<SpotTimeInForce>('GTC')
const sellPercentage = ref(0)

// ====== Computed ======

// Base and quote currency from symbol
const baseCurrency = computed(() => {
  if (!symbol.value) return ''
  return symbol.value.replace(/USDT$/, '')
})

const quoteCurrency = computed(() => 'USDT')

// Available balance from account store
const availableQuote = computed(() => {
  const usdt = accountStore.spotBalances.find(b => b.asset === 'USDT')
  return parseFloat(usdt?.free || '0')
})

const availableBase = computed(() => {
  const btc = accountStore.spotBalances.find(b => b.asset === baseCurrency.value)
  return parseFloat(btc?.free || '0')
})

// Buy side computed
const buyEstimatedAmount = computed(() => {
  if (!buyQuantity.value || !currentPrice.value || currentPrice.value <= 0) {
    return 0
  }
  return buyQuantity.value * currentPrice.value
})

const buyAvailable = computed(() => {
  if (currentPrice.value > 0) {
    return availableQuote.value / currentPrice.value
  }
  return 0
})

const buyPercentageQuantity = computed(() => {
  const maxQty = availableQuote.value / currentPrice.value
  return maxQty * (buyPercentage.value / 100)
})

const buyIsFormValid = computed(() => {
  if (!symbol.value) return false

  // 需要有价格 + (数量 或 成交额)
  if (orderTypeTab.value === 'MARKET') {
    return !!buyQuantity.value || (!!buyInputAmount.value && buyInputAmount.value >= 5)
  }

  if (orderTypeTab.value === 'LIMIT' || orderTypeTab.value === 'STOP') {
    const hasValidAmount = (!!buyQuantity.value) || (!!buyInputAmount.value && buyInputAmount.value >= 5)
    return !!buyPrice.value && hasValidAmount
  }

  return false
})

// Sell side computed
const sellEstimatedAmount = computed(() => {
  if (!sellQuantity.value || !currentPrice.value || currentPrice.value <= 0) {
    return 0
  }
  return sellQuantity.value * currentPrice.value
})

const sellAvailable = computed(() => {
  return availableBase.value
})

const sellPercentageQuantity = computed(() => {
  return availableBase.value * (sellPercentage.value / 100)
})

const sellIsFormValid = computed(() => {
  if (!symbol.value) return false

  // 需要有价格 + (数量 或 成交额)
  if (orderTypeTab.value === 'MARKET') {
    return !!sellQuantity.value || (!!sellInputAmount.value && sellInputAmount.value >= 5)
  }

  if (orderTypeTab.value === 'LIMIT' || orderTypeTab.value === 'STOP') {
    const hasValidAmount = (!!sellQuantity.value) || (!!sellInputAmount.value && sellInputAmount.value >= 5)
    return !!sellPrice.value && hasValidAmount
  }

  return false
})

// ====== Watchers ======

// Order type tab change
watch(orderTypeTab, (newType) => {
  if (newType === 'LIMIT') {
    orderType.value = 'LIMIT'
  } else if (newType === 'MARKET') {
    orderType.value = 'MARKET'
  } else {
    orderType.value = 'STOP_LOSS_LIMIT'
  }
})

// Watch price changes
watch(currentPrice, (newPrice) => {
  if (newPrice > 0 && !buyPrice.value) {
    buyPrice.value = newPrice
  }
  if (newPrice > 0 && !sellPrice.value) {
    sellPrice.value = newPrice
  }
})

// Watch buy percentage changes
watch(buyPercentage, (newPercent) => {
  if (newPercent > 0 && currentPrice.value > 0) {
    buyQuantity.value = buyPercentageQuantity.value
    buyInputAmount.value = buyQuantity.value * currentPrice.value
  }
})

// Watch sell percentage changes
watch(sellPercentage, (newPercent) => {
  if (newPercent > 0) {
    sellQuantity.value = sellPercentageQuantity.value
    sellInputAmount.value = sellQuantity.value * currentPrice.value
  }
})

// Watch buy quantity changes - auto calculate amount
watch(buyQuantity, (newQuantity) => {
  if (newQuantity && currentPrice.value > 0) {
    buyInputAmount.value = newQuantity * currentPrice.value
  }
})

// Watch buy amount changes - auto calculate quantity
watch(buyInputAmount, (newAmount) => {
  if (newAmount && currentPrice.value > 0) {
    buyQuantity.value = newAmount / currentPrice.value
  }
})

// Watch sell quantity changes - auto calculate amount
watch(sellQuantity, (newQuantity) => {
  if (newQuantity && currentPrice.value > 0) {
    sellInputAmount.value = newQuantity * currentPrice.value
  }
})

// Watch sell amount changes - auto calculate quantity
watch(sellInputAmount, (newAmount) => {
  if (newAmount && currentPrice.value > 0) {
    sellQuantity.value = newAmount / currentPrice.value
  }
})

// ====== Methods ======

// Submit buy order
async function submitBuyOrder() {
  if (!buyIsFormValid.value) {
    showMessage('请填写所有必填字段', 'error')
    return
  }

  try {
    let finalQuantity = buyQuantity.value
    let finalQuoteOrderQty: number | undefined

    // 使用成交额模式（市价单用 quoteOrderQty，限价单用计算出的 quantity）
    if (buyInputAmount.value && currentPrice.value > 0) {
      if (orderTypeTab.value === 'MARKET') {
        finalQuoteOrderQty = buyInputAmount.value
        finalQuantity = undefined
      } else {
        finalQuantity = buyInputAmount.value / currentPrice.value
      }
    }

    const order = await createSpotOrder({
      symbol: symbol.value,
      side: 'BUY',
      type: orderType.value,
      quantity: finalQuantity,
      quoteOrderQty: finalQuoteOrderQty,
      price: orderTypeTab.value === 'LIMIT' || orderTypeTab.value === 'STOP' ? buyPrice.value : undefined,
      stopPrice: orderTypeTab.value === 'STOP' ? buyStopPrice.value : undefined,
      timeInForce: orderTypeTab.value === 'LIMIT' ? buyTimeInForce.value : undefined,
    })

    showMessage(`买入成功: ${order.clientOrderId || (order as unknown as Record<string, unknown>).client_order_id}`, 'success')
    resetBuyForm()
  } catch (e) {
    showMessage(error.value || '订单创建失败', 'error')
  }
}

// Submit sell order
async function submitSellOrder() {
  if (!sellIsFormValid.value) {
    showMessage('请填写所有必填字段', 'error')
    return
  }

  try {
    let finalQuantity = sellQuantity.value
    let finalQuoteOrderQty: number | undefined

    // 使用成交额模式（市价单用 quoteOrderQty，限价单用计算出的 quantity）
    if (sellInputAmount.value && currentPrice.value > 0) {
      if (orderTypeTab.value === 'MARKET') {
        finalQuoteOrderQty = sellInputAmount.value
        finalQuantity = undefined
      } else {
        finalQuantity = sellInputAmount.value / currentPrice.value
      }
    }

    const order = await createSpotOrder({
      symbol: symbol.value,
      side: 'SELL',
      type: orderType.value,
      quantity: finalQuantity,
      quoteOrderQty: finalQuoteOrderQty,
      price: orderTypeTab.value === 'LIMIT' || orderTypeTab.value === 'STOP' ? sellPrice.value : undefined,
      stopPrice: orderTypeTab.value === 'STOP' ? sellStopPrice.value : undefined,
      timeInForce: orderTypeTab.value === 'LIMIT' ? sellTimeInForce.value : undefined,
    })

    showMessage(`卖出成功: ${order.clientOrderId || (order as unknown as Record<string, unknown>).client_order_id}`, 'success')
    resetSellForm()
  } catch (e) {
    showMessage(error.value || '订单创建失败', 'error')
  }
}

// Reset forms
function resetBuyForm() {
  buyQuantity.value = undefined
  buyInputAmount.value = undefined
  buyPrice.value = currentPrice.value || undefined
  buyStopPrice.value = undefined
  buyPercentage.value = 0
}

function resetSellForm() {
  sellQuantity.value = undefined
  sellInputAmount.value = undefined
  sellPrice.value = currentPrice.value || undefined
  sellStopPrice.value = undefined
  sellPercentage.value = 0
}

// Format number for display
function formatNumber(value: number | undefined, decimals: number = 4): string {
  if (value === undefined || value === null || isNaN(value)) return '0'
  return value.toFixed(decimals)
}

// Format price for display
function formatPrice(value: number | undefined): string {
  if (value === undefined || value === null || isNaN(value)) return '0'
  if (value < 1) return value.toFixed(6)
  if (value < 100) return value.toFixed(4)
  return value.toFixed(2)
}

// Initialize data on mount
onMounted(async () => {
  // Initialize account store and fetch account data
  accountStore.initialize()
  await accountStore.refreshAccounts()

  // Fetch quotes once via WebSocket (no subscription needed)
  try {
    await connectAndFetchQuote(symbol.value)
    // Set default price for both buy and sell panels
    buyPrice.value = currentPrice.value || undefined
    sellPrice.value = currentPrice.value || undefined
  } catch (e) {
    console.error('[SpotOrderForm] Failed to fetch quote:', e)
  }
})
</script>

<template>
  <NCard :bordered="false" class="spot-order-form">
    <!-- Order Type Tabs -->
    <div class="order-type-tabs">
      <button
        v-for="tab in ['LIMIT', 'MARKET', 'STOP']"
        :key="tab"
        :class="['tab-btn', { active: orderTypeTab === tab }]"
        @click="orderTypeTab = tab as OrderTypeTab"
      >
        {{ tab === 'LIMIT' ? '限价' : tab === 'MARKET' ? '市价' : '止盈止损' }}
      </button>
    </div>

    <!-- Current Price Display -->
    <div class="price-display" v-if="currentPrice > 0">
      <span class="price-label">当前价</span>
      <span class="price-value">{{ formatPrice(currentPrice) }}</span>
    </div>

    <!-- Buy/Sell Panels Side by Side -->
    <div class="order-panels">
      <!-- Buy Panel -->
      <div class="order-panel buy-panel">
        <div class="panel-header">
          <span class="panel-title">买入 {{ baseCurrency }}</span>
        </div>

        <!-- Price Input (for non-MARKET orders) -->
        <div class="input-group" v-if="orderTypeTab !== 'MARKET'">
          <NInputNumber
            v-model:value="buyPrice"
            :min="0"
            :step="0.01"
            :show-button="false"
            placeholder=""
            class="panel-input"
          >
            <template #prefix>
              <span class="input-prefix">价格</span>
            </template>
            <template #suffix>
              <span class="currency-suffix">USDT</span>
            </template>
          </NInputNumber>
        </div>

        <!-- Quantity -->
        <div class="input-group">
          <NInputNumber
            v-model:value="buyQuantity"
            :min="0"
            :step="0.001"
            :show-button="false"
            placeholder=""
            class="panel-input"
          >
            <template #prefix>
              <span class="input-prefix"></span>
            </template>
            <template #suffix>
              <span class="currency-suffix">{{ baseCurrency }}</span>
            </template>
          </NInputNumber>
        </div>

        <!-- Total Amount -->
        <div class="input-group">
          <NInputNumber
            v-model:value="buyInputAmount"
            :min="5"
            :step="1"
            :show-button="false"
            placeholder="最少 5"
            class="panel-input"
          >
            <template #prefix>
              <span class="input-prefix"></span>
            </template>
            <template #suffix>
              <span class="currency-suffix">USDT</span>
            </template>
          </NInputNumber>
        </div>

        <!-- Stop Price (for STOP orders) -->
        <div class="input-group" v-if="orderTypeTab === 'STOP'">
          <NInputNumber
            v-model:value="buyStopPrice"
            :min="0"
            :step="0.01"
            :show-button="false"
            placeholder=""
            class="panel-input"
          >
            <template #prefix>
              <span class="input-prefix">触发</span>
            </template>
            <template #suffix>
              <span class="currency-suffix">USDT</span>
            </template>
          </NInputNumber>
        </div>

        <!-- Percentage Slider -->
        <div class="percentage-slider">
          <NSlider
            v-model:value="buyPercentage"
            :step="1"
            :format-tooltip="(value: number) => `${value}%`"
            :marks="{ 0: '', 25: '', 50: '', 75: '', 100: '' }"
          />
        </div>

        <!-- Panel Info - Available/CanBuy/CanSell -->
        <div class="panel-info">
          <div class="info-row">
            <span class="info-label">可用</span>
            <span class="info-value">{{ formatNumber(availableQuote, 2) }} USDT</span>
          </div>
          <div class="info-row">
            <span class="info-label">可买</span>
            <span class="info-value">{{ formatNumber(buyAvailable, 6) }} {{ baseCurrency }}</span>
          </div>
        </div>

        <!-- Buy Button -->
        <NButton
          type="success"
          :loading="isLoading"
          :disabled="!buyIsFormValid"
          block
          size="large"
          class="submit-btn buy-btn"
          @click="submitBuyOrder"
        >
          买入 {{ baseCurrency }}
        </NButton>
      </div>

      <!-- Sell Panel -->
      <div class="order-panel sell-panel">
        <div class="panel-header">
          <span class="panel-title">卖出 {{ baseCurrency }}</span>
        </div>

        <!-- Price Input (for non-MARKET orders) -->
        <div class="input-group" v-if="orderTypeTab !== 'MARKET'">
          <NInputNumber
            v-model:value="sellPrice"
            :min="0"
            :step="0.01"
            :show-button="false"
            placeholder=""
            class="panel-input"
          >
            <template #prefix>
              <span class="input-prefix">价格</span>
            </template>
            <template #suffix>
              <span class="currency-suffix">USDT</span>
            </template>
          </NInputNumber>
        </div>

        <!-- Quantity -->
        <div class="input-group">
          <NInputNumber
            v-model:value="sellQuantity"
            :min="0"
            :step="0.001"
            :show-button="false"
            placeholder=""
            class="panel-input"
          >
            <template #prefix>
              <span class="input-prefix"></span>
            </template>
            <template #suffix>
              <span class="currency-suffix">{{ baseCurrency }}</span>
            </template>
          </NInputNumber>
        </div>

        <!-- Total Amount -->
        <div class="input-group">
          <NInputNumber
            v-model:value="sellInputAmount"
            :min="5"
            :step="1"
            :show-button="false"
            placeholder="最少 5"
            class="panel-input"
          >
            <template #prefix>
              <span class="input-prefix"></span>
            </template>
            <template #suffix>
              <span class="currency-suffix">USDT</span>
            </template>
          </NInputNumber>
        </div>

        <!-- Stop Price (for STOP orders) -->
        <div class="input-group" v-if="orderTypeTab === 'STOP'">
          <NInputNumber
            v-model:value="sellStopPrice"
            :min="0"
            :step="0.01"
            :show-button="false"
            placeholder=""
            class="panel-input"
          >
            <template #prefix>
              <span class="input-prefix">触发</span>
            </template>
            <template #suffix>
              <span class="currency-suffix">USDT</span>
            </template>
          </NInputNumber>
        </div>

        <!-- Percentage Slider -->
        <div class="percentage-slider">
          <NSlider
            v-model:value="sellPercentage"
            :step="1"
            :format-tooltip="(value: number) => `${value}%`"
            :marks="{ 0: '', 25: '', 50: '', 75: '', 100: '' }"
          />
        </div>

        <!-- Panel Info - Available/CanBuy/CanSell -->
        <div class="panel-info">
          <div class="info-row">
            <span class="info-label">可用</span>
            <span class="info-value">{{ formatNumber(availableBase, 6) }} {{ baseCurrency }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">可卖</span>
            <span class="info-value">{{ formatNumber(sellEstimatedAmount, 2) }} USDT</span>
          </div>
        </div>

        <!-- Sell Button -->
        <NButton
          type="error"
          :loading="isLoading"
          :disabled="!sellIsFormValid"
          block
          size="large"
          class="submit-btn sell-btn"
          @click="submitSellOrder"
        >
          卖出 {{ baseCurrency }}
        </NButton>
      </div>
    </div>
  </NCard>
</template>

<style scoped>
.spot-order-form {
  background: #1a1a2e;
  border-radius: 8px;
  padding: 16px;
}

/* Order Type Tabs */
.order-type-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
  background: #16162a;
  border-radius: 6px;
  padding: 4px;
}

.tab-btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: #8b8b9e;
  font-size: 13px;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
}

.tab-btn.active {
  background: #2a2a4a;
  color: #fff;
}

/* Price Display */
.price-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(0, 192, 135, 0.1);
  border-radius: 4px;
  margin-bottom: 16px;
}

.price-label {
  font-size: 12px;
  color: #8b8b9e;
}

.price-value {
  font-size: 16px;
  color: #00c087;
  font-weight: 600;
}

/* Order Panels - Side by Side */
.order-panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.order-panel {
  background: #16162a;
  border-radius: 8px;
  padding: 16px;
}

.buy-panel {
  border: 1px solid rgba(0, 192, 135, 0.3);
}

.sell-panel {
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.panel-header {
  margin-bottom: 12px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
}

.buy-panel .panel-title {
  color: #00c087;
}

.sell-panel .panel-title {
  color: #ef4444;
}

/* Panel Info */
.panel-info {
  background: #0f0f1a;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.info-row:not(:last-child) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.info-label {
  font-size: 12px;
  color: #8b8b9e;
}

.info-value {
  font-size: 13px;
  color: #fff;
  font-weight: 500;
}

/* Input Groups */
.input-group {
  margin-bottom: 10px;
}

/* Increase input height for price, quantity, amount - use panel-input class for specificity */
.panel-input.n-input-number,
.panel-input .n-input-number,
.input-group .n-input-number,
.input-group .n-input {
  height: 52px !important;
  min-height: 52px !important;
  --n-height: 52px !important;
}

/* Make inner input fill full height */
:deep(.n-input-number input),
:deep(.n-input-number .n-input__input-el),
:deep(.n-input input) {
  height: 52px !important;
  line-height: 52px !important;
  font-size: 14px !important;
  font-weight: 600 !important;
}

/* Currency suffix - same style as input value */
.currency-suffix {
  font-size: 14px !important;
  color: #fff !important;
  font-weight: 600 !important;
}

.input-label {
  font-size: 12px;
  color: #8b8b9e;
  font-weight: 500;
  display: block;
  margin-bottom: 6px;
}

.quantity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.quantity-header .input-label {
  margin-bottom: 0;
}

.mode-toggle {
  font-size: 11px;
  color: #00c087;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 3px;
}

.mode-toggle:hover {
  background: rgba(0, 192, 135, 0.1);
}

.input-prefix {
  font-size: 12px;
  color: #8b8b9e;
  padding-left: 4px;
}

/* Panel Input */
.panel-input {
  width: 100%;
}

/* Panel Input - right align value and placeholder */
.panel-input :deep(.n-input-number-input),
.panel-input :deep(input.n-input-number-input),
.panel-input :deep(.n-input__input-el),
.panel-input :deep(input) {
  text-align: right !important;
  justify-content: flex-end !important;
}

/* Right align placeholder */
.panel-input :deep(.n-input__placeholder) {
  text-align: right !important;
  padding-right: 4px !important;
}

/* Percentage Slider */
.percentage-slider {
  margin-bottom: 16px;
}

.percentage-slider :deep(.n-slider) {
  margin: 0;
}

/* Slider tooltip formatting */
.percentage-slider :deep(.n-slider-tooltip) {
  font-size: 12px;
}

/* Buy panel slider - green theme */
.buy-panel .percentage-slider :deep(.n-slider-rail__fill) {
  background: #00c087;
}

.buy-panel .percentage-slider :deep(.n-slider-handle) {
  border-color: #00c087;
}

.buy-panel .percentage-slider :deep(.n-slider-handle:hover) {
  border-color: #00a06e;
}

/* Sell panel slider - red theme */
.sell-panel .percentage-slider :deep(.n-slider-rail__fill) {
  background: #ef4444;
}

.sell-panel .percentage-slider :deep(.n-slider-handle) {
  border-color: #ef4444;
}

.sell-panel .percentage-slider :deep(.n-slider-handle:hover) {
  border-color: #dc2626;
}

/* Total Section */
.total-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #0f0f1a;
  border-radius: 4px;
  margin-bottom: 12px;
}

.total-label {
  font-size: 12px;
  color: #8b8b9e;
}

.total-value {
  font-size: 14px;
  color: #fff;
  font-weight: 500;
}

/* Submit Button */
.submit-btn {
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  border-radius: 6px;
  color: #fff;
}

.buy-btn {
  background: #00c087;
  border-color: #00c087;
}

.buy-btn:hover {
  background: #00a06e;
  border-color: #00a06e;
}

.sell-btn {
  background: #ef4444;
  border-color: #ef4444;
}

.sell-btn:hover {
  background: #dc2626;
  border-color: #dc2626;
}

/* Override Naive UI input styles */
:deep(.n-input-number) {
  background: #0f0f1a;
  border-color: #2a2a4a;
}

:deep(.n-input-number:focus-within) {
  border-color: #00c087;
}

.buy-panel :deep(.n-input-number:focus-within) {
  border-color: #00c087;
}

.sell-panel :deep(.n-input-number:focus-within) {
  border-color: #ef4444;
}

:deep(.n-input-number__suffix) {
  color: #8b8b9e;
}

:deep(.n-slider) {
  margin: 0;
}

:deep(.n-slider .n-slider-rail__fill) {
  background: #00c087;
}

:deep(.n-slider .n-slider-handle) {
  border-color: #00c087;
}

/* Responsive */
@media (max-width: 640px) {
  .order-panels {
    grid-template-columns: 1fr;
  }
}
</style>
