# 现货交易页面设计文档

> 本文档定义基于后端 WebSocket API 的现货交易前端页面设计

## 1. 后端 API 接口说明

### 1.1 已测试通过的接口

根据 E2E 测试和 WS 协议文档，后端已实现以下接口：

| 消息类型 | 响应类型 | 说明 |
|---------|---------|------|
| `CREATE_ORDER` | `ORDER_DATA` | 创建订单 |
| `GET_ORDER` | `ORDER_DATA` | 查询单个订单 |
| `LIST_ORDERS` | `ORDER_LIST_DATA` | 查询订单列表 |
| `CANCEL_ORDER` | `ORDER_DATA` | 撤销订单 |
| `GET_OPEN_ORDERS` | `ORDER_LIST_DATA` | 查询当前挂单 |

**重要说明**：
- 后端使用 WebSocket 协议，路径：`ws://localhost:8000/ws/trading`
- 当前**仅支持单笔订单**（SINGLE 模式），不支持 OCO/OTO/OTOCO 组合订单
- 订单类型支持：LIMIT, MARKET, STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT, LIMIT_MAKER

### 1.2 ID 生成规范

后端已预设 ID 生成规则，前端必须遵循：

| 字段 | 格式 | 说明 |
|------|------|------|
| `requestId` | UUID v4 hex (32字符) | WS 请求追踪 ID |
| `newClientOrderId` | UUID v4 hex (32字符) | 订单标识 ID（创建订单时使用） |
| `origClientOrderId` | UUID v4 hex (32字符) | 订单标识 ID（查询/取消订单时使用） |

```typescript
// ID 生成函数 (必须使用)
function generateRequestId(): string {
  return crypto.randomUUID().replace(/-/g, '')  // 32字符hex
}

function generateClientOrderId(): string {
  return crypto.randomUUID().replace(/-/g, '')  // 32字符hex
}
```

### 1.3 期货/现货区分

通过 symbol 格式区分（**前端需要添加前缀**）：

| 市场 | Symbol 格式 | 示例 |
|------|-------------|------|
| 现货 | 添加 `BINANCE:` 前缀 | `BINANCE:BTCUSDT` |
| 期货 | 添加 `BINANCE:` 前缀 + `.PERP` 后缀 | `BINANCE:BTCUSDT.PERP` |

> **重要**：前端发送时必须添加 `BINANCE:` 前缀，后端不再自动添加

### 1.4 请求消息格式

```typescript
// WebSocket 请求格式
interface WSRequest {
  protocolVersion: '2.0'
  type: string           // CREATE_ORDER, GET_ORDER, etc.
  requestId: string       // 前端生成，UUID v4 hex
  timestamp: number       // Unix 毫秒时间戳
  data: object           // 业务数据
}
```

### 1.5 CREATE_ORDER 必填参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `symbol` | string | 交易对 (如 `BINANCE:BTCUSDT`) |
| `side` | string | 方向 (`BUY` / `SELL`) |
| `type` | string | 订单类型 |
| `quantity` | number | 数量 |
| `newClientOrderId` | string | 订单标识 ID (UUID格式) |

> **重要**：根据协议文档 v2.4，创建订单必须使用 `newClientOrderId` 字段

### 1.6 订单类型参数矩阵

| 订单类型 | quantity | quoteOrderQty | price | stopPrice | timeInForce |
|----------|----------|---------------|-------|-----------|-------------|
| LIMIT | 必填 | - | 必填 | - | 条件必填 |
| MARKET | 条件必填 | 条件必填 | - | - | - |
| STOP_LOSS | 必填 | - | - | 必填 | - |
| STOP_LOSS_LIMIT | 必填 | - | 必填 | 必填 | 条件必填 |
| TAKE_PROFIT | 必填 | - | - | 必填 | - |
| TAKE_PROFIT_LIMIT | 必填 | - | 必填 | 必填 | 条件必填 |
| LIMIT_MAKER | 必填 | - | 必填 | - | - |

### 1.7 现货特有参数

| 参数 | 类型 | 说明 | 适用订单类型 |
|------|------|------|-------------|
| `quoteOrderQty` | number | 报价数量（以 USDT 计价） | MARKET（现货市价单） |
| `icebergQty` | number | 冰山订单隐藏数量 | LIMIT, STOP_LOSS_LIMIT, TAKE_PROFIT_LIMIT |
| `trailingDelta` | number | 跟踪止损价格偏移量 | STOP_LOSS, STOP_LOSS_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT |
| `strategyId` | number | 策略ID | 所有类型 |
| `strategyType` | number | 策略类型（必须 >= 1000000） | 所有类型 |
| `selfTradePreventionMode` | string | 自成交预防模式 | 所有类型 |
| `newOrderRespType` | string | 响应格式：ACK/RESULT/FULL | 所有类型 |

> **注意**：以上参数为现货特有，期货（U本位合约）使用不同的参数集（如 `positionSide`, `reduceOnly`, `priceMatch` 等）

---

## 2. 页面布局设计

### 2.1 整体布局 (单页设计)

```
┌────────────────────────────────────────────────────────────────┐
│                        市场信息栏                                │
│  [交易对: BTCUSDT ▼]  价格: 50,234.56   涨跌幅: +2.34%       │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    订单参数表单                           │  │
│  │                                                          │  │
│  │  交易对: [BTCUSDT                        ]               │  │
│  │                                                          │  │
│  │  方向:  [ 买入 ● ]    [ 卖出 ○ ]                        │  │
│  │                                                          │  │
│  │  订单类型: [限价单                          ▼]           │  │
│  │                                                          │  │
│  │  数量: [0.001                          ]  BTC             │  │
│  │                                                          │  │
│  │  价格: [50000                         ]  USDT            │  │
│  │                                                          │  │
│  │  有效期: [GTC - 成交为止              ▼]                │  │
│  │                                                          │  │
│  │  ┌─ 高级选项 (点击展开) ─────────────────────────────┐  │  │
│  │  │ 触发价格: [____________] USDT                      │  │  │
│  │  │ 冰山数量: [____________]                          │  │  │
│  │  │ STP模式: [EXPIRE_MAKER                        ▼] │  │  │
│  │  │ 策略ID: [____________]                            │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐  │  │
│  │  │              [        买入 BTC       ]             │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. 订单参数表单设计

### 3.1 交易对输入

```vue
<template>
  <NFormItem label="交易对">
    <NSelect
      v-model:value="symbol"
      :options="symbolOptions"
      filterable
      placeholder="选择或输入交易对"
    />
  </NFormItem>
</template>

<script setup>
// 常用交易对选项
const symbolOptions = [
  { label: 'BTCUSDT', value: 'BTCUSDT' },
  { label: 'ETHUSDT', value: 'ETHUSDT' },
  { label: 'BNBUSDT', value: 'BNBUSDT' },
  { label: 'SOLUSDT', value: 'SOLUSDT' },
  { label: 'XRPUSDT', value: 'XRPUSDT' },
]
</script>
```

### 3.2 方向选择

```vue
<template>
  <div class="side-selector">
    <NButton
      :type="side === 'BUY' ? 'success' : 'default'"
      @click="side = 'BUY'"
    >
      买入
    </NButton>
    <NButton
      :type="side === 'SELL' ? 'error' : 'default'"
      @click="side = 'SELL'"
    >
      卖出
    </NButton>
  </div>
</template>
```

### 3.3 订单类型选择

```typescript
// 现货订单类型选项
const orderTypeOptions = [
  { label: '限价单 (LIMIT)', value: 'LIMIT' },
  { label: '市价单 (MARKET)', value: 'MARKET' },
  { label: '止损单 (STOP_LOSS)', value: 'STOP_LOSS' },
  { label: '止损限价单 (STOP_LOSS_LIMIT)', value: 'STOP_LOSS_LIMIT' },
  { label: '止盈单 (TAKE_PROFIT)', value: 'TAKE_PROFIT' },
  { label: '止盈限价单 (TAKE_PROFIT_LIMIT)', value: 'TAKE_PROFIT_LIMIT' },
  { label: '只做Maker (LIMIT_MAKER)', value: 'LIMIT_MAKER' },
]
```

### 3.4 数量/报价数量输入

```vue
<template>
  <!-- 现货市价单显示报价数量 -->
  <NFormItem v-if="showQuoteOrderQty" label="报价数量">
    <NInputNumber v-model:value="quoteOrderQty" :min="0" />
    <template #feedback>
      市价买入: 花费这么多USDT买入
      市价卖出: 卖出这么多换取USDT
    </template>
  </NFormItem>

  <!-- 其他情况显示基础数量 -->
  <NFormItem v-else label="数量">
    <NInputNumber v-model:value="quantity" :min="0" :step="0.001" />
  </NFormItem>
</template>

<script setup>
// 现货市价单可使用 quoteOrderQty
const showQuoteOrderQty = computed(() => {
  return orderType.value === 'MARKET'
})
</script>
```

---

## 4. 高级选项设计

### 4.1 高级选项面板

```vue
<NCollapse>
  <NCollapseItem title="高级选项" name="advanced">
    <!-- 触发价格 (止损/止盈单) -->
    <NFormItem v-if="showStopPrice" label="触发价格">
      <NInputNumber v-model:value="stopPrice" :min="0" />
    </NFormItem>

    <!-- 冰山数量 -->
    <NFormItem v-if="showIcebergQty" label="冰山数量">
      <NInputNumber v-model:value="icebergQty" :min="0" />
    </NFormItem>

    <!-- 追踪止损 Delta -->
    <NFormItem v-if="showTrailingDelta" label="追踪Delta">
      <NInputNumber v-model:value="trailingDelta" :min="0" />
    </NFormItem>

    <!-- STP 模式 -->
    <NFormItem label="STP模式">
      <NSelect v-model:value="selfTradePreventionMode" :options="stpModeOptions" />
    </NFormItem>

    <!-- 策略参数 -->
    <NFormItem label="策略ID">
      <NInputNumber v-model:value="strategyId" :min="0" />
    </NFormItem>

    <NFormItem label="策略类型">
      <NInputNumber v-model:value="strategyType" :min="1000000" />
    </NFormItem>
  </NCollapseItem>
</NCollapse>
```

### 4.2 高级选项显示条件

```typescript
// 触发价格显示条件
const showStopPrice = computed(() => {
  return ['STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value)
})

// 冰山数量显示条件
const showIcebergQty = computed(() => {
  return ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value)
})

// 追踪Delta显示条件
const showTrailingDelta = computed(() => {
  return ['STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value)
})
```

---

## 5. API 调用实现

### 5.1 创建订单函数

```typescript
// 位于: src/composables/useSpotOrder.ts

import { sendMessage } from '../stores/trading-store'

/**
 * 创建现货订单
 * 使用后端规定的 ID 格式
 */
async function createSpotOrder(params: {
  symbol: string        // e.g., 'BTCUSDT'
  side: 'BUY' | 'SELL'
  type: SingleOrderType
  quantity?: number
  quoteOrderQty?: number
  price?: number
  stopPrice?: number
  timeInForce?: 'GTC' | 'IOC' | 'FOK'
  icebergQty?: number
  trailingDelta?: number
  strategyId?: number
  strategyType?: number
  selfTradePreventionMode?: string
  newOrderRespType?: 'ACK' | 'RESULT' | 'FULL'
}): Promise<Order> {
  // 前端生成 requestId (UUID v4 hex, 32字符)
  const requestId = crypto.randomUUID().replace(/-/g, '')

  // 前端生成 newClientOrderId (UUID v4 hex, 32字符)
  const newClientOrderId = crypto.randomUUID().replace(/-/g, '')

  // 构建请求数据 (使用 camelCase)
  const orderData = {
    symbol: params.symbol,                    // 现货格式: BINANCE:BTCUSDT
    side: params.side,
    type: params.type,
    newClientOrderId,                         // 使用 newClientOrderId
    ...(params.quantity && { quantity: params.quantity }),
    ...(params.quoteOrderQty && { quoteOrderQty: params.quoteOrderQty }),
    ...(params.price && { price: params.price }),
    ...(params.stopPrice && { stopPrice: params.stopPrice }),
    ...(params.timeInForce && { timeInForce: params.timeInForce }),
    ...(params.icebergQty && { icebergQty: params.icebergQty }),
    ...(params.trailingDelta && { trailingDelta: params.trailingDelta }),
    ...(params.strategyId && { strategyId: params.strategyId }),
    ...(params.strategyType && { strategyType: params.strategyType }),
    ...(params.selfTradePreventionMode && { selfTradePreventionMode: params.selfTradePreventionMode }),
    ...(params.newOrderRespType && { newOrderRespType: params.newOrderRespType }),
  }

  // 发送 WebSocket 请求
  return await sendMessage('CREATE_ORDER', orderData)
}
```

### 5.2 查询订单

```typescript
/**
 * 查询单个订单
 */
async function getOrder(symbol: string, orderId?: number, origClientOrderId?: string) {
  const data: Record<string, unknown> = { symbol }

  if (orderId) {
    data.orderId = orderId
  } else if (origClientOrderId) {
    data.origClientOrderId = origClientOrderId  // 查询订单使用 origClientOrderId
  }

  return await sendMessage('GET_ORDER', data)
}
```

### 5.3 取消订单

```typescript
/**
 * 取消订单
 * 重要：根据协议文档，取消订单使用 origClientOrderId（下单时传入的客户端订单ID）
 */
async function cancelOrder(symbol: string, orderId?: number, origClientOrderId?: string) {
  const data: Record<string, unknown> = { symbol }

  if (orderId) {
    data.orderId = orderId
  } else if (origClientOrderId) {
    data.origClientOrderId = origClientOrderId  // 取消订单使用 origClientOrderId
  }

  return await sendMessage('CANCEL_ORDER', data)
}
```

### 5.4 查询订单列表

```typescript
/**
 * 查询订单列表
 */
async function listOrders(params: {
  symbol: string
  startTime?: number
  endTime?: number
  limit?: number
  status?: string
}) {
  return await sendMessage('LIST_ORDERS', params)
}

/**
 * 查询当前挂单
 */
async function getOpenOrders(symbol?: string) {
  const data = symbol ? { symbol } : {}
  return await sendMessage('GET_OPEN_ORDERS', data)
}
```

---

## 6. 表单验证规则

### 6.1 必填字段验证

```typescript
const validationRules = {
  // 交易对验证
  symbol: (value: string) => {
    if (!value) return '请输入交易对'
    if (!/^[A-Z]{2,10}(USDT|BTC|ETH|BNB|TRX)$/i.test(value)) {
      return '交易对格式错误'
    }
    return true
  },

  // 数量验证
  quantity: (value: number | undefined, orderType: string) => {
    if (!value || value <= 0) return '数量必须大于 0'
    return true
  },

  // 报价数量验证
  quoteOrderQty: (value: number | undefined) => {
    if (!value || value <= 0) return '报价数量必须大于 0'
    return true
  },

  // 价格验证
  price: (value: number | undefined) => {
    if (!value || value <= 0) return '价格必须大于 0'
    return true
  },

  // 触发价格验证
  stopPrice: (value: number | undefined) => {
    if (!value || value <= 0) return '触发价格必须大于 0'
    return true
  },
}
```

### 6.2 条件必填验证

```typescript
// 计算表单是否有效
const isFormValid = computed(() => {
  // 交易对
  if (!symbol.value) return false

  // 数量 (市价单可以用 quoteOrderQty)
  if (orderType.value === 'MARKET') {
    if (!quantity.value && !quoteOrderQty.value) return false
  } else {
    if (!quantity.value) return false
  }

  // 价格 (限价单必填)
  if (showPrice.value && !price.value) return false

  // 触发价格 (止损/止盈单必填)
  if (showStopPrice.value && !stopPrice.value) return false

  return true
})
```

---

## 7. 组件设计

### 7.1 组件结构

```
src/
├── components/
│   └── trading/
│       ├── SpotOrderForm.vue          # 主表单组件
│       ├── OrderSideSelector.vue       # 买卖方向选择
│       ├── OrderTypeSelect.vue        # 订单类型选择
│       ├── QuantityInput.vue          # 数量输入
│       ├── PriceInput.vue             # 价格输入
│       ├── StopPriceInput.vue         # 触发价格输入
│       ├── TimeInForceSelect.vue      # 有效期选择
│       └── AdvancedOptions.vue        # 高级选项
├── composables/
│   └── useSpotOrder.ts                # 订单逻辑
└── stores/
    └── trading-store.ts               # 交易状态管理
```

### 7.2 主组件 SpotOrderForm.vue

```vue
<script setup lang="ts">
import { ref, computed } from 'vue'
import { NForm, NFormItem, NSelect, NInputNumber, NButton, NCard, NCollapse, NCollapseItem, NSpace } from 'naive-ui'
import { useTradingStore } from '../../stores/trading-store'

// Types
type OrderSide = 'BUY' | 'SELL'
type OrderType = 'LIMIT' | 'MARKET' | 'STOP_LOSS' | 'STOP_LOSS_LIMIT' | 'TAKE_PROFIT' | 'TAKE_PROFIT_LIMIT' | 'LIMIT_MAKER'
type TimeInForce = 'GTC' | 'IOC' | 'FOK'

// Store
const tradingStore = useTradingStore()

// Form State
const symbol = ref<string>('')
const side = ref<OrderSide>('BUY')
const orderType = ref<OrderType>('LIMIT')
const quantity = ref<number | undefined>(undefined)
const quoteOrderQty = ref<number | undefined>(undefined)
const price = ref<number | undefined>(undefined)
const stopPrice = ref<number | undefined>(undefined)
const timeInForce = ref<TimeInForce>('GTC')
const icebergQty = ref<number | undefined>(undefined)
const trailingDelta = ref<number | undefined>(undefined)
const strategyId = ref<number | undefined>(undefined)
const strategyType = ref<number | undefined>(undefined)
const selfTradePreventionMode = ref<string>('EXPIRE_MAKER')
const newOrderRespType = ref<string>('FULL')

// Options
const orderTypeOptions = [
  { label: '限价单 (LIMIT)', value: 'LIMIT' },
  { label: '市价单 (MARKET)', value: 'MARKET' },
  { label: '止损单 (STOP_LOSS)', value: 'STOP_LOSS' },
  { label: '止损限价单 (STOP_LOSS_LIMIT)', value: 'STOP_LOSS_LIMIT' },
  { label: '止盈单 (TAKE_PROFIT)', value: 'TAKE_PROFIT' },
  { label: '止盈限价单 (TAKE_PROFIT_LIMIT)', value: 'TAKE_PROFIT_LIMIT' },
  { label: '只做Maker (LIMIT_MAKER)', value: 'LIMIT_MAKER' },
]

const timeInForceOptions = [
  { label: 'GTC - 成交为止', value: 'GTC' },
  { label: 'IOC - 立即成交或取消', value: 'IOC' },
  { label: 'FOK - 全部成交或取消', value: 'FOK' },
]

const stpModeOptions = [
  { label: 'NONE - 不启用', value: 'NONE' },
  { label: 'EXPIRE_MAKER', value: 'EXPIRE_MAKER' },
  { label: 'EXPIRE_TAKER', value: 'EXPIRE_TAKER' },
  { label: 'EXPIRE_BOTH', value: 'EXPIRE_BOTH' },
  { label: 'DECREMENT', value: 'DECREMENT' },
  { label: 'TRANSFER', value: 'TRANSFER' },
]

// Computed
const showPrice = computed(() => ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT', 'LIMIT_MAKER'].includes(orderType.value))
const showStopPrice = computed(() => ['STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value))
const showTimeInForce = computed(() => ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value))
const showQuoteOrderQty = computed(() => orderType.value === 'MARKET')
const showIcebergQty = computed(() => ['LIMIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value))
const showTrailingDelta = computed(() => ['STOP_LOSS', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT', 'TAKE_PROFIT_LIMIT'].includes(orderType.value))

// Submit
async function submitOrder() {
  const newClientOrderId = crypto.randomUUID().replace(/-/g, '')

  const orderData = {
    symbol: `BINANCE:${symbol.value}`,  // 添加 BINANCE: 前缀
    side: side.value,
    type: orderType.value,
    newClientOrderId,
    ...(quantity.value && { quantity: quantity.value }),
    ...(quoteOrderQty.value && { quoteOrderQty: quoteOrderQty.value }),
    ...(price.value && { price: price.value }),
    ...(stopPrice.value && { stopPrice: stopPrice.value }),
    ...(timeInForce.value && { timeInForce: timeInForce.value }),
    ...(icebergQty.value && { icebergQty: icebergQty.value }),
    ...(trailingDelta.value && { trailingDelta: trailingDelta.value }),
    ...(strategyId.value && { strategyId: strategyId.value }),
    ...(strategyType.value && { strategyType: strategyType.value }),
    ...(selfTradePreventionMode.value !== 'NONE' && { selfTradePreventionMode: selfTradePreventionMode.value }),
    ...(newOrderRespType.value !== 'FULL' && { newOrderRespType: newOrderRespType.value }),
  }

  await tradingStore.createOrder(orderData as any)
}
</script>

<template>
  <NCard title="现货下单">
    <NForm label-placement="top">
      <!-- 交易对 -->
      <NFormItem label="交易对">
        <NInput v-model:value="symbol" placeholder="BTCUSDT" />
      </NFormItem>

      <!-- 方向 -->
      <NFormItem label="方向">
        <NSpace>
          <NButton :type="side === 'BUY' ? 'success' : 'default'" @click="side = 'BUY'">
            买入
          </NButton>
          <NButton :type="side === 'SELL' ? 'error' : 'default'" @click="side = 'SELL'">
            卖出
          </NButton>
        </NSpace>
      </NFormItem>

      <!-- 订单类型 -->
      <NFormItem label="订单类型">
        <NSelect v-model:value="orderType" :options="orderTypeOptions" />
      </NFormItem>

      <!-- 数量/报价数量 -->
      <NFormItem v-if="showQuoteOrderQty" label="报价数量">
        <NInputNumber v-model:value="quoteOrderQty" :min="0" style="width: 100%" />
      </NFormItem>
      <NFormItem v-else label="数量">
        <NInputNumber v-model:value="quantity" :min="0" :step="0.001" style="width: 100%" />
      </NFormItem>

      <!-- 价格 -->
      <NFormItem v-if="showPrice" label="价格">
        <NInputNumber v-model:value="price" :min="0" style="width: 100%" />
      </NFormItem>

      <!-- 触发价格 -->
      <NFormItem v-if="showStopPrice" label="触发价格">
        <NInputNumber v-model:value="stopPrice" :min="0" style="width: 100%" />
      </NFormItem>

      <!-- 有效期 -->
      <NFormItem v-if="showTimeInForce" label="有效期">
        <NSelect v-model:value="timeInForce" :options="timeInForceOptions" />
      </NFormItem>

      <!-- 高级选项 -->
      <NCollapse>
        <NCollapseItem title="高级选项" name="advanced">
          <NFormItem v-if="showIcebergQty" label="冰山数量">
            <NInputNumber v-model:value="icebergQty" :min="0" style="width: 100%" />
          </NFormItem>

          <NFormItem v-if="showTrailingDelta" label="追踪Delta">
            <NInputNumber v-model:value="trailingDelta" :min="0" style="width: 100%" />
          </NFormItem>

          <NFormItem label="STP模式">
            <NSelect v-model:value="selfTradePreventionMode" :options="stpModeOptions" />
          </NFormItem>

          <NFormItem label="策略ID">
            <NInputNumber v-model:value="strategyId" :min="0" style="width: 100%" />
          </NFormItem>

          <NFormItem label="策略类型">
            <NInputNumber v-model:value="strategyType" :min="1000000" style="width: 100%" />
          </NFormItem>
        </NCollapseItem>
      </NCollapse>

      <!-- 提交按钮 -->
      <NFormItem>
        <NButton
          :type="side === 'BUY' ? 'success' : 'error'"
          :loading="tradingStore.isLoading"
          block
          @click="submitOrder"
        >
          {{ side === 'BUY' ? '买入' : '卖出' }} {{ symbol || '' }}
        </NButton>
      </NFormItem>
    </NForm>
  </NCard>
</template>
```

---

## 8. 注意事项

### 8.1 ID 格式要求

- `requestId` 必须使用 **UUID v4 hex 格式（32字符）**
- 创建订单使用 `newClientOrderId`（UUID v4 hex 格式）
- 查询/取消订单使用 `origClientOrderId`（下单时传入的客户端订单ID）
- 不能使用自定义字符串或短 ID
- 必须使用 `crypto.randomUUID().replace(/-/g, '')` 生成

### 8.2 Symbol 格式

- **现货**：必须添加 `BINANCE:` 前缀，如 `BINANCE:BTCUSDT`
- **期货**：必须添加 `BINANCE:` 前缀 + `.PERP` 后缀，如 `BINANCE:BTCUSDT.PERP`

### 8.3 字段命名

- 前端发送使用 **camelCase**（如 `newClientOrderId`）
- 后端使用 SnakeCaseModel 自动转换为 snake_case（如 `new_client_order_id`）
- 响应中返回的字段可能使用不同命名，需根据实际响应处理

### 8.4 响应处理流程

1. **第一阶段**：发送请求后立即收到 `ACK` 确认（可选）
2. **第二阶段**：订单处理完成后收到 `ORDER_DATA` 或 `ORDER_LIST_DATA`
3. **错误响应**：`type` 为 `ERROR`，错误信息在 `data` 中

### 8.5 字段名使用场景

| 操作 | 字段名 | 说明 |
|------|--------|------|
| 创建订单 | `newClientOrderId` | 前端生成，用于标识订单 |
| 查询订单 | `orderId` 或 `origClientOrderId` | 二选一 |
| 取消订单 | `orderId` 或 `origClientOrderId` | 二选一 |

> **重要**：`origClientOrderId` 是下单时传入的 `newClientOrderId` 值，用于查询和取消订单时标识订单。

---

## 9. 参考文档

- [WebSocket 协议规范](./07-websocket-protocol.md)
- [订单任务表设计](./04-trading-orders.md)
- [Trading Store 实现](./trading-store.ts)
- [E2E 测试用例](./ws-order.spec.ts)

---

**版本**: v1.1
**更新**: 2026-03-09 - 修复审核报告问题

### 修改记录 (v1.1)

1. **字段名修正**：`clientOrderId` → `newClientOrderId`（创建订单）
2. **字段名修正**：查询/取消订单使用 `origClientOrderId`
3. **Symbol 格式**：明确使用 `BINANCE:` 前缀
4. **补充说明**：添加字段名使用场景表
