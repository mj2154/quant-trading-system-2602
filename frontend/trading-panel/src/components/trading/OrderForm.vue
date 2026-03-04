<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  NForm,
  NFormItem,
  NSelect,
  NInputNumber,
  NInput,
  NButton,
  NCard,
  NSwitch,
  NSpace,
  NAlert,
  NCollapse,
  NCollapseItem,
} from 'naive-ui'
import { useTradingStore } from '../../stores/trading-store'
import type { MarketType, OrderSide, OrderType, PositionSide, TimeInForce, SelfTradePreventionMode, PriceMatch, NewOrderRespType } from '../../types/trading-types'

// Store
const tradingStore = useTradingStore()

// Form state
const marketType = ref<MarketType>('FUTURES')
const symbol = ref<string>('')
const symbolError = ref<string | null>(null)
const side = ref<OrderSide>('BUY')
const orderType = ref<OrderType>('LIMIT')
const quantity = ref<number | undefined>(undefined)
const quoteOrderQty = ref<number | undefined>(undefined)  // 现货市价单报价数量
const price = ref<number | undefined>(undefined)
const stopPrice = ref<number | undefined>(undefined)
const timeInForce = ref<TimeInForce>('GTC')
const positionSide = ref<PositionSide>('BOTH')
const reduceOnly = ref(false)

// 高级选项
const newClientOrderId = ref<string>('')
const newOrderRespType = ref<NewOrderRespType>('ACK')
const selfTradePreventionMode = ref<SelfTradePreventionMode>('EXPIRE_MAKER')
const icebergQty = ref<number | undefined>(undefined)
const trailingDelta = ref<number | undefined>(undefined)
const strategyId = ref<number | undefined>(undefined)
const strategyType = ref<number | undefined>(undefined)
const priceMatch = ref<PriceMatch>('NONE')
const goodTillDate = ref<number | undefined>(undefined)

// Error state
const errorMessage = ref<string | null>(null)

// Options - 市场类型
const marketTypeOptions = [
  { label: 'U本位合约', value: 'FUTURES' },
  { label: '现货', value: 'SPOT' },
]

// Options - 订单类型
const futuresOrderTypeOptions = [
  { label: '限价单 (LIMIT)', value: 'LIMIT' },
  { label: '市价单 (MARKET)', value: 'MARKET' },
  { label: '止损单 (STOP)', value: 'STOP' },
  { label: '止损限价单 (STOP_LOSS_LIMIT)', value: 'STOP_LOSS_LIMIT' },
  { label: '止盈单 (TAKE_PROFIT)', value: 'TAKE_PROFIT' },
  { label: '止盈限价单 (TAKE_PROFIT_LIMIT)', value: 'TAKE_PROFIT_LIMIT' },
  { label: '跟踪止损 (TRAILING_STOP_MARKET)', value: 'TRAILING_STOP_MARKET' },
  { label: '只做maker (LIMIT_MAKER)', value: 'LIMIT_MAKER' },
]

const spotOrderTypeOptions = [
  { label: '限价单 (LIMIT)', value: 'LIMIT' },
  { label: '市价单 (MARKET)', value: 'MARKET' },
  { label: '止损单 (STOP_LOSS)', value: 'STOP_LOSS' },
  { label: '止损限价单 (STOP_LOSS_LIMIT)', value: 'STOP_LOSS_LIMIT' },
  { label: '止盈单 (TAKE_PROFIT)', value: 'TAKE_PROFIT' },
  { label: '止盈限价单 (TAKE_PROFIT_LIMIT)', value: 'TAKE_PROFIT_LIMIT' },
  { label: '只做maker (LIMIT_MAKER)', value: 'LIMIT_MAKER' },
]

// Options - 有效期
const timeInForceOptions = [
  { label: 'GTC - 成交为止', value: 'GTC' },
  { label: 'IOC - 立即成交或取消', value: 'IOC' },
  { label: 'FOK - 全部成交或取消', value: 'FOK' },
  { label: 'GTD - 指定时间前有效', value: 'GTD' },
]

// Options - 持仓方向
const positionSideOptions = [
  { label: '单向持仓', value: 'BOTH' },
  { label: '做多', value: 'LONG' },
  { label: '做空', value: 'SHORT' },
]

// Options - 自成交预防模式
const stpModeOptions = [
  { label: 'EXPIRE_MAKER - maker订单过期', value: 'EXPIRE_MAKER' },
  { label: 'EXPIRE_TAKER - taker订单过期', value: 'EXPIRE_TAKER' },
  { label: 'EXPIRE_BOTH - 双方订单都过期', value: 'EXPIRE_BOTH' },
  { label: 'NONE - 不启用', value: 'NONE' },
]

// Options - 响应类型
const newOrderRespTypeOptions = [
  { label: 'ACK - 仅返回确认', value: 'ACK' },
  { label: 'RESULT - 返回结果', value: 'RESULT' },
  { label: 'FULL - 返回完整信息', value: 'FULL' },
]

// Options - 价格匹配 (期货)
const priceMatchOptions = [
  { label: 'NONE - 不启用', value: 'NONE' },
  { label: 'OPPONENT - 对手价', value: 'OPPONENT' },
  { label: 'OPPONENT_5 - 对手价滑点5档', value: 'OPPONENT_5' },
  { label: 'OPPONENT_10 - 对手价滑点10档', value: 'OPPONENT_10' },
  { label: 'OPPONENT_20 - 对手价滑点20档', value: 'OPPONENT_20' },
  { label: 'QUEUE - 队列价', value: 'QUEUE' },
  { label: 'QUEUE_5 - 队列价滑点5档', value: 'QUEUE_5' },
  { label: 'QUEUE_10 - 队列价滑点10档', value: 'QUEUE_10' },
  { label: 'QUEUE_20 - 队列价滑点20档', value: 'QUEUE_20' },
]

// Computed
const isFutures = computed(() => marketType.value === 'FUTURES')
const isSpot = computed(() => marketType.value === 'SPOT')

const currentOrderTypeOptions = computed(() => {
  return isFutures.value ? futuresOrderTypeOptions : spotOrderTypeOptions
})

const showPrice = computed(() => {
  return ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value)
})

const showStopPrice = computed(() => {
  return ['STOP', 'STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value)
})

const showTimeInForce = computed(() => {
  return ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value)
})

const showPositionSide = computed(() => isFutures.value)

const showReduceOnly = computed(() => isFutures.value)

// 现货专用
const showQuoteOrderQty = computed(() => {
  return isSpot.value && orderType.value === 'MARKET'
})

const showIcebergQty = computed(() => {
  return isSpot.value && ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value)
})

const showTrailingDelta = computed(() => {
  return ['STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value)
})

// 期货专用
const showPriceMatch = computed(() => {
  return isFutures.value && ['LIMIT', 'STOP', 'TAKE_PROFIT'].includes(orderType.value)
})

const showGoodTillDate = computed(() => {
  return timeInForce.value === 'GTD'
})

const showTrailingStopMarket = computed(() => {
  return isFutures.value && orderType.value === 'TRAILING_STOP_MARKET'
})

// 验证交易对格式 (例如 BTCUSDT, ETHUSDT)
function validateSymbol(value: string): string | null {
  if (!value) {
    return '请输入交易对'
  }
  const normalized = value.toUpperCase().trim()
  // 基本格式检查: 大写字母, 3-12个字符, 必须以可能的报价资产结尾
  if (!/^[A-Z]{2,10}(USDT|BTC|ETH|BNB|TRX)$/.test(normalized)) {
    return '交易对格式错误 (例如: BTCUSDT, ETHUSDT)'
  }
  return null
}

// 验证表单
const isFormValid = computed(() => {
  const symbolValidation = validateSymbol(symbol.value)
  if (symbolValidation || !symbol.value) return false

  // 市价单必须有 quantity 或 quoteOrderQty
  if (orderType.value === 'MARKET') {
    if (isSpot.value) {
      if (!quantity.value && !quoteOrderQty.value) return false
    } else {
      if (!quantity.value) return false
    }
  } else {
    if (!quantity.value) return false
  }

  // 限价单必须有价格
  if (showPrice.value && !price.value) return false
  // 止损/止盈单必须有触发价格
  if (showStopPrice.value && !stopPrice.value) return false
  // GTD订单必须有过期时间
  if (showGoodTillDate.value && !goodTillDate.value) return false
  return true
})

// 监听交易对变化清除错误
watch(symbol, () => {
  if (symbolError.value) {
    symbolError.value = null
  }
})

// 监听订单类型变化重置价格相关字段
watch(orderType, () => {
  if (!showPrice.value) {
    price.value = undefined
  }
  if (!showStopPrice.value) {
    stopPrice.value = undefined
  }
  if (orderType.value !== 'TRAILING_STOP_MARKET') {
    trailingDelta.value = undefined
  }
})

// 监听市场类型变化
watch(marketType, () => {
  // 切换市场时重置一些选项
  if (isSpot.value) {
    positionSide.value = 'BOTH'
    reduceOnly.value = false
    priceMatch.value = 'NONE'
  } else {
    quoteOrderQty.value = undefined
    icebergQty.value = undefined
    strategyId.value = undefined
    strategyType.value = undefined
  }
})

// Methods
function setSide(newSide: OrderSide) {
  side.value = newSide
}

// 生成客户端订单ID
function generateClientOrderId(): string {
  if (newClientOrderId.value) {
    return newClientOrderId.value
  }
  return `ord_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`
}

async function submitOrder() {
  errorMessage.value = null
  symbolError.value = null

  // 提交前验证交易对
  const symbolValidation = validateSymbol(symbol.value)
  if (symbolValidation) {
    symbolError.value = symbolValidation
    return
  }

  if (!isFormValid.value) {
    errorMessage.value = '请填写所有必填字段'
    return
  }

  try {
    const clientOrderId = generateClientOrderId()

    // 构建订单参数
    const orderParams: Record<string, unknown> = {
      marketType: marketType.value,
      symbol: symbol.value.toUpperCase().trim(),
      side: side.value,
      orderType: orderType.value,
      clientOrderId,
    }

    // 数量
    if (orderType.value === 'MARKET' && isSpot.value && quoteOrderQty.value) {
      orderParams.quoteOrderQty = quoteOrderQty.value
    } else if (quantity.value) {
      orderParams.quantity = quantity.value
    }

    // 价格相关
    if (showPrice.value && price.value) {
      orderParams.price = price.value
    }
    if (showStopPrice.value && stopPrice.value) {
      orderParams.stopPrice = stopPrice.value
    }
    if (showTimeInForce.value && timeInForce.value) {
      orderParams.timeInForce = timeInForce.value
    }

    // 期货专用
    if (isFutures.value) {
      if (showReduceOnly.value) {
        orderParams.reduceOnly = reduceOnly.value
      }
      if (showPositionSide.value && positionSide.value !== 'BOTH') {
        orderParams.positionSide = positionSide.value
      }
      if (showPriceMatch.value && priceMatch.value !== 'NONE') {
        orderParams.priceMatch = priceMatch.value
      }
      if (showGoodTillDate.value && goodTillDate.value) {
        orderParams.goodTillDate = goodTillDate.value
      }
      if (newOrderRespType.value !== 'ACK') {
        orderParams.newOrderRespType = newOrderRespType.value
      }
    }

    // 现货专用
    if (isSpot.value) {
      if (showIcebergQty.value && icebergQty.value) {
        orderParams.icebergQty = icebergQty.value
      }
      if (showTrailingDelta.value && trailingDelta.value) {
        orderParams.trailingDelta = trailingDelta.value
      }
      if (strategyId.value) {
        orderParams.strategyId = strategyId.value
      }
      if (strategyType.value && strategyType.value >= 1000000) {
        orderParams.strategyType = strategyType.value
      }
      if (selfTradePreventionMode.value !== 'NONE') {
        orderParams.selfTradePreventionMode = selfTradePreventionMode.value
      }
    }

    // 跟踪止损市价单
    if (showTrailingStopMarket.value && trailingDelta.value) {
      orderParams.trailingDelta = trailingDelta.value
    }

    await tradingStore.createOrder(orderParams as any)

    // 成功后重置表单
    quantity.value = undefined
    quoteOrderQty.value = undefined
    price.value = undefined
    stopPrice.value = undefined
    newClientOrderId.value = ''
  } catch (e) {
    errorMessage.value = e instanceof Error ? e.message : '创建订单失败'
  }
}

// 计算GTD最小时间
const minGoodTillDate = computed(() => {
  return Date.now() + 600 * 1000  // 当前时间 + 600秒
})
</script>

<template>
  <NCard title="创建订单" size="small">
    <NForm label-placement="top" label-width="100">
      <!-- 市场类型 -->
      <NFormItem label="市场" data-testid="market-type-select">
        <NSelect
          v-model:value="marketType"
          :options="marketTypeOptions"
          placeholder="选择市场"
        />
      </NFormItem>

      <!-- 交易对 -->
      <NFormItem label="交易对" data-testid="symbol-input" :feedback-status="symbolError ? 'error' : undefined">
        <NInput
          v-model:value="symbol"
          placeholder="BTCUSDT"
          style="width: 100%"
          :status="symbolError ? 'error' : undefined"
        />
        <template #feedback>
          <span v-if="symbolError">{{ symbolError }}</span>
        </template>
      </NFormItem>

      <!-- 买卖方向 -->
      <NFormItem label="方向" data-testid="side-buttons">
        <NSpace>
          <NButton
            data-testid="buy-button"
            :type="side === 'BUY' ? 'success' : 'default'"
            @click="setSide('BUY')"
          >
            买入
          </NButton>
          <NButton
            data-testid="sell-button"
            :type="side === 'SELL' ? 'error' : 'default'"
            @click="setSide('SELL')"
          >
            卖出
          </NButton>
        </NSpace>
      </NFormItem>

      <!-- 订单类型 -->
      <NFormItem label="订单类型" data-testid="order-type-select">
        <NSelect
          v-model:value="orderType"
          :options="currentOrderTypeOptions"
          placeholder="选择订单类型"
        />
      </NFormItem>

      <!-- 数量 (基础资产) -->
      <NFormItem v-if="!showQuoteOrderQty" label="数量" data-testid="quantity-input">
        <NInputNumber
          v-model:value="quantity"
          :min="0"
          :step="0.001"
          placeholder="数量"
          style="width: 100%"
        />
      </NFormItem>

      <!-- 报价数量 (现货市价单) -->
      <NFormItem v-if="showQuoteOrderQty" label="报价数量" data-testid="quote-order-qty-input">
        <NInputNumber
          v-model:value="quoteOrderQty"
          :min="0"
          :step="1"
          placeholder="使用报价资产数量 (例如 USDT)"
          style="width: 100%"
        />
        <template #feedback>
          <span style="font-size: 12px; color: #999;">
            市价买入时: 花费这么多USDT买入BTC<br>
            市价卖出时: 卖出这么多BTC换取USDT
          </span>
        </template>
      </NFormItem>

      <!-- 价格 (限价单) -->
      <NFormItem v-if="showPrice" label="价格" data-testid="price-input">
        <NInputNumber
          v-model:value="price"
          :min="0"
          :step="0.01"
          placeholder="价格"
          style="width: 100%"
        />
      </NFormItem>

      <!-- 触发价格 (止损/止盈单) -->
      <NFormItem v-if="showStopPrice" label="触发价格" data-testid="stop-price-input">
        <NInputNumber
          v-model:value="stopPrice"
          :min="0"
          :step="0.01"
          placeholder="触发价格"
          style="width: 100%"
        />
      </NFormItem>

      <!-- 跟踪止损Delta -->
      <NFormItem v-if="showTrailingDelta || showTrailingStopMarket" label="跟踪Delta" data-testid="trailing-delta-input">
        <NInputNumber
          v-model:value="trailingDelta"
          :min="0"
          :step="1"
          placeholder="跟踪止损价格偏移量"
          style="width: 100%"
        />
        <template #feedback>
          <span style="font-size: 12px; color: #999;">
            价格偏移量，用于跟踪止损
          </span>
        </template>
      </NFormItem>

      <!-- 有效期 (限价单) -->
      <NFormItem v-if="showTimeInForce" label="有效期" data-testid="time-in-force-select">
        <NSelect
          v-model:value="timeInForce"
          :options="timeInForceOptions"
          placeholder="选择有效期"
        />
      </NFormItem>

      <!-- GTD过期时间 -->
      <NFormItem v-if="showGoodTillDate" label="过期时间" data-testid="good-till-date-input">
        <NInputNumber
          v-model:value="goodTillDate"
          :min="minGoodTillDate"
          :step="1000"
          placeholder="过期时间戳(毫秒)"
          style="width: 100%"
        />
        <template #feedback>
          <span style="font-size: 12px; color: #999;">
            必须大于当前时间+600秒
          </span>
        </template>
      </NFormItem>

      <!-- 持仓方向 (期货) -->
      <NFormItem v-if="showPositionSide" label="持仓" data-testid="position-side-select">
        <NSelect
          v-model:value="positionSide"
          :options="positionSideOptions"
          placeholder="选择持仓方向"
        />
      </NFormItem>

      <!-- 只减仓 (期货) -->
      <NFormItem v-if="showReduceOnly" label="只减仓" data-testid="reduce-only-checkbox">
        <NSwitch v-model:value="reduceOnly" />
        <template #feedback>
          <span style="font-size: 12px; color: #999;">
            仅减少持仓，不增加仓位
          </span>
        </template>
      </NFormItem>

      <!-- 价格匹配 (期货) -->
      <NFormItem v-if="showPriceMatch" label="价格匹配" data-testid="price-match-select">
        <NSelect
          v-model:value="priceMatch"
          :options="priceMatchOptions"
          placeholder="选择价格匹配模式"
        />
        <template #feedback>
          <span style="font-size: 12px; color: #999;">
            智能订单，自动匹配最优价格
          </span>
        </template>
      </NFormItem>

      <!-- 高级选项 -->
      <NCollapse>
        <NCollapseItem title="高级选项" name="advanced">
          <!-- 客户端订单ID -->
          <NFormItem label="客户端订单ID" data-testid="client-order-id-input">
            <NInput
              v-model:value="newClientOrderId"
              placeholder="自定义订单ID (可选)"
              style="width: 100%"
            />
          </NFormItem>

          <!-- 响应类型 (期货) -->
          <NFormItem v-if="isFutures" label="响应类型" data-testid="response-type-select">
            <NSelect
              v-model:value="newOrderRespType"
              :options="newOrderRespTypeOptions"
              placeholder="选择响应类型"
            />
          </NFormItem>

          <!-- 自成交预防 (现货) -->
          <NFormItem v-if="isSpot" label="STP模式" data-testid="stp-mode-select">
            <NSelect
              v-model:value="selfTradePreventionMode"
              :options="stpModeOptions"
              placeholder="选择STP模式"
            />
          </NFormItem>

          <!-- 冰山订单 (现货) -->
          <NFormItem v-if="showIcebergQty" label="冰山数量" data-testid="iceberg-qty-input">
            <NInputNumber
              v-model:value="icebergQty"
              :min="0"
              :step="0.001"
              placeholder="冰山订单隐藏数量"
              style="width: 100%"
            />
            <template #feedback>
              <span style="font-size: 12px; color: #999;">
                只显示部分数量，其余隐藏在冰山订单中
              </span>
            </template>
          </NFormItem>

          <!-- 策略ID (现货) -->
          <NFormItem v-if="isSpot" label="策略ID" data-testid="strategy-id-input">
            <NInputNumber
              v-model:value="strategyId"
              :min="0"
              :step="1"
              placeholder="策略ID (可选)"
              style="width: 100%"
            />
          </NFormItem>

          <!-- 策略类型 (现货) -->
          <NFormItem v-if="isSpot" label="策略类型" data-testid="strategy-type-input">
            <NInputNumber
              v-model:value="strategyType"
              :min="1000000"
              :step="1"
              placeholder="策略类型 (必须 >= 1000000)"
              style="width: 100%"
            />
          </NFormItem>
        </NCollapseItem>
      </NCollapse>

      <!-- 错误提示 -->
      <NFormItem v-if="errorMessage" data-testid="error-message">
        <NAlert type="error">{{ errorMessage }}</NAlert>
      </NFormItem>

      <!-- 提交按钮 -->
      <NFormItem>
        <NButton
          data-testid="submit-button"
          :type="side === 'BUY' ? 'success' : 'error'"
          :loading="tradingStore.isLoading"
          :disabled="!isFormValid"
          block
          @click="submitOrder"
        >
          {{ side === 'BUY' ? '买入' : '卖出' }} {{ symbol || '?' }}
        </NButton>
      </NFormItem>
    </NForm>
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

/* Form label styling */
:deep(.n-form-item-label) {
  color: #94A3B8 !important;
  font-size: 13px;
  font-weight: 500;
}

/* Input styling for dark theme */
:deep(.n-input) {
  --n-border: 1px solid rgba(245, 158, 11, 0.2);
  --n-border-hover: 1px solid rgba(245, 158, 11, 0.4);
  --n-border-focus: 1px solid #F59E0B;
  --n-color: rgba(15, 23, 42, 0.8);
  --n-color-focus: rgba(15, 23, 42, 0.9);
}

:deep(.n-input .n-input__input-el) {
  color: #F8FAFC;
}

:deep(.n-input .n-input__input-el::placeholder) {
  color: #64748B;
}

/* Select styling */
:deep(.n-base-selection) {
  --n-border: 1px solid rgba(245, 158, 11, 0.2);
  --n-border-hover: 1px solid rgba(245, 158, 11, 0.4);
  --n-border-focus: 1px solid #F59E0B;
  --n-color: rgba(15, 23, 42, 0.8);
  --n-color-focus: rgba(15, 23, 42, 0.9);
}

:deep(.n-base-selection-label) {
  color: #F8FAFC;
}

/* Number input styling */
:deep(.n-input-number) {
  --n-border: 1px solid rgba(245, 158, 11, 0.2);
  --n-border-hover: 1px solid rgba(245, 158, 11, 0.4);
  --n-border-focus: 1px solid #F59E0B;
  --n-color: rgba(15, 23, 42, 0.8);
}

:deep(.n-input-number .n-input-number-input) {
  color: #F8FAFC;
}

/* Switch styling */
:deep(.n-switch.n-switch--active) {
  --n-rail-color-active: #F59E0B;
}

/* Button styling */
:deep(.n-button) {
  font-weight: 600;
  letter-spacing: 0.5px;
  transition: all 0.2s ease;
}

:deep(.n-button:hover) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

/* Collapse styling */
:deep(.n-collapse) {
  background: transparent;
}

:deep(.n-collapse-item__header) {
  color: #94A3B8;
}

:deep(.n-collapse-item__content-inner) {
  padding-top: 12px;
}

/* Feedback text color */
:deep(.n-form-item .n-form-item-feedback) {
  color: #64748B;
  font-size: 12px;
}

/* Alert styling */
:deep(.n-alert) {
  --n-color: rgba(239, 68, 68, 0.15);
  --n-border: 1px solid rgba(239, 68, 68, 0.3);
}
</style>
