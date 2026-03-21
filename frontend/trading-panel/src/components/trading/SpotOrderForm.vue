<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  NCard,
  NButton,
  NSlider,
} from 'naive-ui'
import { useSpotOrder } from '../../composables/useSpotOrder'
import { dataService } from '../../services/data-service/DataService'
import type { SpotOrderType, OrderTimeInForce } from '../../types/api'
import { useAccountStore } from '../../stores/account-store'
import { getSymbolFilters } from '../../libs/symbol-filters'
import { roundToStep, getDecimalPlaces } from '../../libs/format'
import NumberInput from '../common/NumberInput.vue'
import StepperButtons from '../common/StepperButtons.vue'

// Types
type OrderSide = 'BUY' | 'SELL'
type OrderTypeTab = 'LIMIT' | 'MARKET' | 'STOP'

// Composables
const { createSpotOrder, isLoading, error } = useSpotOrder()
const accountStore = useAccountStore()

// Current price from quotes (WebSocket)
const currentPrice = ref<number>(0)

// 使用 DataService 获取报价
async function fetchQuote(targetSymbol: string): Promise<void> {
  try {
    const response = await dataService.getQuotes([`BINANCE:${targetSymbol}`])
    if (response.quotes && response.quotes.length > 0) {
      const quote = response.quotes[0]
      // DataService 返回的报价格式: { lp: lastPrice, ... }
      currentPrice.value = parseFloat((quote as any).v?.lp) || 0
      console.log('[SpotOrderForm] Quote price:', currentPrice.value)
    }
  } catch (e) {
    console.error('[SpotOrderForm] Failed to fetch quote:', e)
    throw e
  }
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
const buyPrice = ref<number | null>(null)
const buyQuantity = ref<number | null>(null)
const buyInputAmount = ref<number | null>(null)
const buyStopPrice = ref<number | null>(null)
const buyTimeInForce = ref<OrderTimeInForce>('GTC')
const buyPercentage = ref(0)

// NumberInput refs for stepper buttons
const buyPriceInputRef = ref<InstanceType<typeof NumberInput> | null>(null)
const buyQuantityInputRef = ref<InstanceType<typeof NumberInput> | null>(null)
const buyAmountInputRef = ref<InstanceType<typeof NumberInput> | null>(null)
const buyStopPriceInputRef = ref<InstanceType<typeof NumberInput> | null>(null)

// Sell side state
const sellPrice = ref<number | null>(null)
const sellQuantity = ref<number | null>(null)
const sellInputAmount = ref<number | null>(null)
const sellStopPrice = ref<number | null>(null)
const sellTimeInForce = ref<OrderTimeInForce>('GTC')
const sellPercentage = ref(0)

// NumberInput refs for stepper buttons (sell side)
const sellPriceInputRef = ref<InstanceType<typeof NumberInput> | null>(null)
const sellQuantityInputRef = ref<InstanceType<typeof NumberInput> | null>(null)
const sellAmountInputRef = ref<InstanceType<typeof NumberInput> | null>(null)
const sellStopPriceInputRef = ref<InstanceType<typeof NumberInput> | null>(null)

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

// Watch buy percentage changes - auto calculate quantity and amount
watch(buyPercentage, (newPercent) => {
  if (newPercent > 0 && currentPrice.value > 0) {
    const qty = roundQuantity(buyPercentageQuantity.value)
    buyQuantity.value = qty
    buyInputAmount.value = (qty || 0) * currentPrice.value
  }
})

// Watch sell percentage changes - auto calculate quantity and amount
watch(sellPercentage, (newPercent) => {
  if (newPercent > 0) {
    const qty = roundQuantity(sellPercentageQuantity.value)
    sellQuantity.value = qty
    sellInputAmount.value = (qty || 0) * currentPrice.value
  }
})

// Watch buy quantity changes - auto calculate amount (仅计算，不回写)
watch(buyQuantity, (newQuantity) => {
  if (newQuantity && currentPrice.value > 0) {
    buyInputAmount.value = newQuantity * currentPrice.value
  }
})

// Watch buy amount changes - auto calculate quantity (仅计算，不回写)
watch(buyInputAmount, (newAmount) => {
  if (newAmount && currentPrice.value > 0) {
    const rawQty = newAmount / currentPrice.value
    const qty = roundQuantity(rawQty)
    buyQuantity.value = qty
  }
})

// Watch sell quantity changes - auto calculate amount (仅计算，不回写)
watch(sellQuantity, (newQuantity) => {
  if (newQuantity && currentPrice.value > 0) {
    sellInputAmount.value = newQuantity * currentPrice.value
  }
})

// Watch sell amount changes - auto calculate quantity (仅计算，不回写)
watch(sellInputAmount, (newAmount) => {
  if (newAmount && currentPrice.value > 0) {
    const rawQty = newAmount / currentPrice.value
    const qty = roundQuantity(rawQty)
    sellQuantity.value = qty
  }
})

// ====== Methods ======

/**
 * 舍入数量到 stepSize 的整数倍
 * 确保满足币安 LOT_SIZE 过滤器要求
 */
function roundQuantity(quantity: number | null): number | null {
  if (quantity === null || quantity <= 0) return null
  const filters = getSymbolFilters(symbol.value)
  return roundToStep(quantity, filters.lotSize.stepSize, 'floor')
}

/**
 * 舍入价格到 tickSize 的整数倍
 * 确保满足币安 PRICE_FILTER 过滤器要求
 */
function roundPrice(price: number | null): number | null {
  if (price === null || price <= 0) return null
  const filters = getSymbolFilters(symbol.value)
  return roundToStep(price, filters.priceFilter.tickSize, 'floor')
}

// Submit buy order
async function submitBuyOrder() {
  if (!buyIsFormValid.value) {
    showMessage('请填写所有必填字段', 'error')
    return
  }

  try {
    let finalQuantity = buyQuantity.value
    let finalQuoteOrderQty: number | null = null

    // 使用成交额模式（市价单用 quoteOrderQty，限价单用计算出的 quantity）
    if (buyInputAmount.value && currentPrice.value > 0) {
      if (orderTypeTab.value === 'MARKET') {
        // 市价单成交额舍入到2位小数（满足币安对quote asset的精度要求）
        finalQuoteOrderQty = roundToStep(buyInputAmount.value, 0.01, 'floor')
        finalQuantity = null
      } else {
        finalQuantity = buyInputAmount.value / currentPrice.value
      }
    }

    // 舍入数量到 stepSize 的整数倍（满足币安 LOT_SIZE 要求）
    finalQuantity = roundQuantity(finalQuantity)
    // 舍入价格到 tickSize 的整数倍（满足币安 PRICE_FILTER 要求）
    const finalPrice = roundPrice(buyPrice.value)
    const finalStopPrice = roundPrice(buyStopPrice.value)

    // 检查数量是否有效
    if (finalQuantity === null || finalQuantity <= 0) {
      showMessage('请输入有效的数量', 'error')
      return
    }

    // 检查价格是否有效（对于限价单）
    if ((orderTypeTab.value === 'LIMIT' || orderTypeTab.value === 'STOP') && !finalPrice) {
      showMessage('请输入有效的价格', 'error')
      return
    }

    const order = await createSpotOrder({
      symbol: symbol.value,
      side: 'BUY',
      type: orderType.value,
      quantity: finalQuantity,
      quoteOrderQty: finalQuoteOrderQty,
      price: orderTypeTab.value === 'LIMIT' || orderTypeTab.value === 'STOP' ? finalPrice : null,
      stopPrice: orderTypeTab.value === 'STOP' ? finalStopPrice : null,
      timeInForce: orderTypeTab.value === 'LIMIT' ? buyTimeInForce.value : null,
    })

    showMessage(`买入成功: ${order.clientOrderId || (order as unknown as Record<string, unknown>).client_order_id}`, 'success')
    resetBuyForm()
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : '订单创建失败'
    showMessage(errorMessage, 'error')
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
    let finalQuoteOrderQty: number | null = null

    // 使用成交额模式（市价单用 quoteOrderQty，限价单用计算出的 quantity）
    if (sellInputAmount.value && currentPrice.value > 0) {
      if (orderTypeTab.value === 'MARKET') {
        // 市价单成交额舍入到2位小数（满足币安对quote asset的精度要求）
        finalQuoteOrderQty = roundToStep(sellInputAmount.value, 0.01, 'floor')
        finalQuantity = null
      } else {
        finalQuantity = sellInputAmount.value / currentPrice.value
      }
    }

    // 舍入数量到 stepSize 的整数倍（满足币安 LOT_SIZE 要求）
    finalQuantity = roundQuantity(finalQuantity)
    // 舍入价格到 tickSize 的整数倍（满足币安 PRICE_FILTER 要求）
    const finalPrice = roundPrice(sellPrice.value)
    const finalStopPrice = roundPrice(sellStopPrice.value)

    // 检查数量是否有效
    if (finalQuantity === null || finalQuantity <= 0) {
      showMessage('请输入有效的数量', 'error')
      return
    }

    // 检查价格是否有效（对于限价单）
    if ((orderTypeTab.value === 'LIMIT' || orderTypeTab.value === 'STOP') && !finalPrice) {
      showMessage('请输入有效的价格', 'error')
      return
    }

    const order = await createSpotOrder({
      symbol: symbol.value,
      side: 'SELL',
      type: orderType.value,
      quantity: finalQuantity,
      quoteOrderQty: finalQuoteOrderQty,
      price: orderTypeTab.value === 'LIMIT' || orderTypeTab.value === 'STOP' ? finalPrice : null,
      stopPrice: orderTypeTab.value === 'STOP' ? finalStopPrice : null,
      timeInForce: orderTypeTab.value === 'LIMIT' ? sellTimeInForce.value : null,
    })

    showMessage(`卖出成功: ${order.clientOrderId || (order as unknown as Record<string, unknown>).client_order_id}`, 'success')
    resetSellForm()
  } catch (e) {
    const errorMessage = e instanceof Error ? e.message : '订单创建失败'
    showMessage(errorMessage, 'error')
  }
}

// Reset forms
function resetBuyForm() {
  buyQuantity.value = null
  buyInputAmount.value = null
  buyPrice.value = currentPrice.value || null
  buyStopPrice.value = null
  buyPercentage.value = 0
}

function resetSellForm() {
  sellQuantity.value = null
  sellInputAmount.value = null
  sellPrice.value = currentPrice.value || null
  sellStopPrice.value = null
  sellPercentage.value = 0
}

// Format number for display
function formatQuantityForDisplay(value: number | undefined): string {
  if (value === undefined || value === null || isNaN(value)) return '0'
  // 使用交易对的 stepSize 对应的小数位数
  const filters = getSymbolFilters(symbol.value)
  const decimals = getDecimalPlaces(filters.lotSize.stepSize)
  return value.toFixed(decimals)
}

// Format number for display (通用版本，用于余额等)
function formatNumber(value: number | undefined, decimals: number = 4): string {
  if (value === undefined || value === null || isNaN(value)) return '0'
  return value.toFixed(decimals)
}

// Format price for display
function formatPriceForDisplay(value: number | undefined): string {
  if (value === undefined || value === null || isNaN(value)) return '0'
  // 使用交易对的 tickSize 对应的小数位数
  const filters = getSymbolFilters(symbol.value)
  const decimals = getDecimalPlaces(filters.priceFilter.tickSize)
  return value.toFixed(decimals)
}

// Format price for display (通用版本)
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

  // Fetch quotes once via DataService
  try {
    await fetchQuote(symbol.value)
    // Set default price for both buy and sell panels
    buyPrice.value = currentPrice.value || null
    sellPrice.value = currentPrice.value || null
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
          <NumberInput
            ref="buyPriceInputRef"
            v-model="buyPrice"
            prefix="价格"
            suffix="USDT"
            :precision="getDecimalPlaces(getSymbolFilters(symbol).priceFilter.tickSize)"
            :step-size="getSymbolFilters(symbol).priceFilter.tickSize"
            :min="getSymbolFilters(symbol).priceFilter.minPrice"
            :max="getSymbolFilters(symbol).priceFilter.maxPrice"
            theme="buy"
            placeholder=""
          />
          <StepperButtons
            theme="buy"
            :disabled="orderTypeTab === 'MARKET'"
            @increment="buyPriceInputRef?.stepIncrement()"
            @decrement="buyPriceInputRef?.stepDecrement()"
          />
        </div>

        <!-- Quantity -->
        <div class="input-group">
          <NumberInput
            ref="buyQuantityInputRef"
            v-model="buyQuantity"
            prefix="数量"
            :suffix="baseCurrency"
            :precision="getDecimalPlaces(getSymbolFilters(symbol).lotSize.stepSize)"
            :step-size="getSymbolFilters(symbol).lotSize.stepSize"
            :min="getSymbolFilters(symbol).lotSize.minQty"
            :max="getSymbolFilters(symbol).lotSize.maxQty"
            theme="buy"
            placeholder=""
          />
          <StepperButtons
            theme="buy"
            @increment="buyQuantityInputRef?.stepIncrement()"
            @decrement="buyQuantityInputRef?.stepDecrement()"
          />
        </div>

        <!-- Total Amount -->
        <div class="input-group">
          <NumberInput
            ref="buyAmountInputRef"
            v-model="buyInputAmount"
            prefix="成交额"
            suffix="USDT"
            :precision="2"
            :step-size="1"
            :min="5"
            theme="buy"
            placeholder="最少 5"
          />
          <StepperButtons
            theme="buy"
            @increment="buyAmountInputRef?.stepIncrement()"
            @decrement="buyAmountInputRef?.stepDecrement()"
          />
        </div>

        <!-- Stop Price (for STOP orders) -->
        <div class="input-group" v-if="orderTypeTab === 'STOP'">
          <NumberInput
            ref="buyStopPriceInputRef"
            v-model="buyStopPrice"
            prefix="触发"
            suffix="USDT"
            :precision="getDecimalPlaces(getSymbolFilters(symbol).priceFilter.tickSize)"
            :step-size="getSymbolFilters(symbol).priceFilter.tickSize"
            :min="getSymbolFilters(symbol).priceFilter.minPrice"
            :max="getSymbolFilters(symbol).priceFilter.maxPrice"
            theme="buy"
            placeholder=""
          />
          <StepperButtons
            theme="buy"
            @increment="buyStopPriceInputRef?.stepIncrement()"
            @decrement="buyStopPriceInputRef?.stepDecrement()"
          />
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
          :disabled="!buyIsFormValid || isLoading"
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
          <NumberInput
            ref="sellPriceInputRef"
            v-model="sellPrice"
            prefix="价格"
            suffix="USDT"
            :precision="getDecimalPlaces(getSymbolFilters(symbol).priceFilter.tickSize)"
            :step-size="getSymbolFilters(symbol).priceFilter.tickSize"
            :min="getSymbolFilters(symbol).priceFilter.minPrice"
            :max="getSymbolFilters(symbol).priceFilter.maxPrice"
            theme="sell"
            placeholder=""
          />
          <StepperButtons
            theme="sell"
            :disabled="orderTypeTab === 'MARKET'"
            @increment="sellPriceInputRef?.stepIncrement()"
            @decrement="sellPriceInputRef?.stepDecrement()"
          />
        </div>

        <!-- Quantity -->
        <div class="input-group">
          <NumberInput
            ref="sellQuantityInputRef"
            v-model="sellQuantity"
            prefix="数量"
            :suffix="baseCurrency"
            :precision="getDecimalPlaces(getSymbolFilters(symbol).lotSize.stepSize)"
            :step-size="getSymbolFilters(symbol).lotSize.stepSize"
            :min="getSymbolFilters(symbol).lotSize.minQty"
            :max="getSymbolFilters(symbol).lotSize.maxQty"
            theme="sell"
            placeholder=""
          />
          <StepperButtons
            theme="sell"
            @increment="sellQuantityInputRef?.stepIncrement()"
            @decrement="sellQuantityInputRef?.stepDecrement()"
          />
        </div>

        <!-- Total Amount -->
        <div class="input-group">
          <NumberInput
            ref="sellAmountInputRef"
            v-model="sellInputAmount"
            prefix="成交额"
            suffix="USDT"
            :precision="2"
            :step-size="1"
            :min="5"
            theme="sell"
            placeholder="最少 5"
          />
          <StepperButtons
            theme="sell"
            @increment="sellAmountInputRef?.stepIncrement()"
            @decrement="sellAmountInputRef?.stepDecrement()"
          />
        </div>

        <!-- Stop Price (for STOP orders) -->
        <div class="input-group" v-if="orderTypeTab === 'STOP'">
          <NumberInput
            ref="sellStopPriceInputRef"
            v-model="sellStopPrice"
            prefix="触发"
            suffix="USDT"
            :precision="getDecimalPlaces(getSymbolFilters(symbol).priceFilter.tickSize)"
            :step-size="getSymbolFilters(symbol).priceFilter.tickSize"
            :min="getSymbolFilters(symbol).priceFilter.minPrice"
            :max="getSymbolFilters(symbol).priceFilter.maxPrice"
            theme="sell"
            placeholder=""
          />
          <StepperButtons
            theme="sell"
            @increment="sellStopPriceInputRef?.stepIncrement()"
            @decrement="sellStopPriceInputRef?.stepDecrement()"
          />
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
          :disabled="!sellIsFormValid || isLoading"
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
  margin-right: 4px;
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
  background: #00875a !important;
  border-color: #00875a !important;
  color: #ffffff !important;
}

.buy-btn:hover {
  background: #006644 !important;
  border-color: #006644 !important;
  color: #ffffff !important;
}

.sell-btn {
  background: #dc2626 !important;
  border-color: #dc2626 !important;
  color: #ffffff !important;
}

.sell-btn:hover {
  background: #b91c1c !important;
  border-color: #b91c1c !important;
  color: #ffffff !important;
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

/* Native Input Styles */
.native-input-wrapper {
  display: flex;
  align-items: center;
  background: #0f0f1a;
  border: 1px solid #2a2a4a;
  border-radius: 4px;
  height: 52px;
  padding: 0 12px;
  transition: border-color 0.2s;
  flex: 1;
}

.native-input-wrapper:focus-within {
  border-color: #00c087;
}

.buy-panel .native-input-wrapper:focus-within {
  border-color: #00c087;
}

.sell-panel .native-input-wrapper:focus-within {
  border-color: #ef4444;
}

.native-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  text-align: right;
  height: 100%;
  padding: 0;
  margin-right: 8px;
}

.native-input::placeholder {
  color: #4a4a5a;
  text-align: right;
}

/* Input group with stepper buttons */
.input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Responsive */
@media (max-width: 640px) {
  .order-panels {
    grid-template-columns: 1fr;
  }
}
</style>
