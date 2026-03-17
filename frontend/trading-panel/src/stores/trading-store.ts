import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { dataService } from '../services/data-service/DataService'
import type {
  Order,
  CreateOrderParams,
  OrderFilters,
  OrderUpdate,
  OrderListResponse,
} from '../types/api'

// Development mode flag
const isDev = import.meta.env.DEV

// Logger utility
function log(level: 'log' | 'error', message: string, ...args: unknown[]) {
  if (level === 'error' || isDev) {
    console[level](`[TradingStore] ${message}`, ...args)
  }
}

export const useTradingStore = defineStore('trading', () => {
  // State
  const orders = ref<Order[]>([])
  const openOrders = ref<Order[]>([])
  const currentOrder = ref<Order | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdate = ref(new Date())

  // Computed
  const hasOpenOrders = computed(() => openOrders.value.length > 0)

  // 通过 symbol 前缀区分市场类型：.PERP 结尾为期货
  const isFuturesSymbol = (symbol: string) => symbol.endsWith('.PERP')

  const ordersByMarket = computed(() => {
    const result: Record<'FUTURES' | 'SPOT', Order[]> = {
      FUTURES: [],
      SPOT: [],
    }
    orders.value.forEach((order) => {
      const marketType = isFuturesSymbol(order.symbol) ? 'FUTURES' : 'SPOT'
      result[marketType].push(order)
    })
    return result
  })

  // Actions
  async function createOrder(params: CreateOrderParams): Promise<Order> {
    isLoading.value = true
    error.value = null

    try {
      // Validate required params
      if (!params.symbol || !params.side || !params.orderType) {
        throw new Error('Missing required order parameters')
      }

      // Validate quantity for MARKET orders (spot can use quoteOrderQty)
      // 通过 symbol 前缀区分市场类型：.PERP 结尾为期货
      const isSpot = !params.symbol.endsWith('.PERP')
      if (params.orderType === 'MARKET') {
        if (isSpot) {
          if (!params.quantity && !params.quoteOrderQty) {
            throw new Error('Quantity or quoteOrderQty is required for spot market orders')
          }
        } else {
          if (!params.quantity) {
            throw new Error('Quantity is required for futures market orders')
          }
        }
      } else {
        if (!params.quantity) {
          throw new Error('Quantity is required')
        }
      }

      // Validate price for limit orders
      if (
        (params.orderType === 'LIMIT' || params.orderType === 'STOP' || params.orderType === 'TAKE_PROFIT') &&
        !params.price &&
        !params.priceMatch  // priceMatch can replace price
      ) {
        throw new Error('Price is required for limit orders')
      }

      // Validate stopPrice for stop orders
      if (
        (params.orderType === 'STOP' || params.orderType === 'STOP_MARKET' || params.orderType === 'TAKE_PROFIT' || params.orderType === 'TAKE_PROFIT_MARKET') &&
        !params.stopPrice &&
        !params.trailingDelta  // trailingDelta can replace stopPrice
      ) {
        throw new Error('Stop price or trailingDelta is required for stop orders')
      }

      // Validate trailingDelta for TRAILING_STOP_MARKET
      if (params.orderType === 'TRAILING_STOP_MARKET' && !params.trailingDelta) {
        throw new Error('TrailingDelta is required for trailing stop orders')
      }

      // Validate goodTillDate for GTD orders (GTD is only supported in futures)
      // 期货使用 .PERP 后缀
      if (params.goodTillDate && !isSpot && !params.timeInForce) {
        throw new Error('timeInForce is required when goodTillDate is set')
      }

      const clientOrderId = generateRequestId()

      // Create order locally first (optimistic update)
      const newOrder: Order = {
        clientOrderId,
        symbol: params.symbol,
        side: params.side,
        orderType: params.orderType,
        status: 'NEW',
        data: {
          quantity: params.quantity,
          quoteOrderQty: params.quoteOrderQty,
          price: params.price,
          timeInForce: params.timeInForce,
          stopPrice: params.stopPrice,
          reduceOnly: params.reduceOnly,
          positionSide: params.positionSide,
          // 高级参数
          newClientOrderId: params.newClientOrderId,
          newOrderRespType: params.newOrderRespType,
          selfTradePreventionMode: params.selfTradePreventionMode,
          icebergQty: params.icebergQty,
          trailingDelta: params.trailingDelta,
          strategyId: params.strategyId,
          strategyType: params.strategyType,
          priceMatch: params.priceMatch,
          goodTillDate: params.goodTillDate,
        },
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }

      // Add to orders immediately (immutable update)
      orders.value = [...orders.value, newOrder]
      openOrders.value = [...openOrders.value, newOrder]
      lastUpdate.value = new Date()

      // Send to server
      try {
        // 使用 DataService 创建订单
        const response = await dataService.createOrder({
          ...params,
          clientOrderId,
        })

        // Update order with server response (immutable update)
        const index = orders.value.findIndex((o) => o.clientOrderId === clientOrderId)
        if (index !== -1) {
          orders.value = orders.value.map((o, i) =>
            i === index ? { ...o, ...response } : o
          )
        }

        return orders.value[index]
      } catch (e) {
        // Server request failed, mark order as rejected (immutable update)
        const index = orders.value.findIndex((o) => o.clientOrderId === clientOrderId)
        if (index !== -1) {
          orders.value = orders.value.map((o, i) =>
            i === index ? { ...o, status: 'REJECTED', updatedAt: new Date().toISOString() } : o
          )

          // Remove from open orders (immutable update)
          openOrders.value = openOrders.value.filter((o) => o.clientOrderId !== clientOrderId)
        }
        throw e
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create order'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchOrder(clientOrderId: string): Promise<Order | null> {
    isLoading.value = true
    error.value = null

    try {
      // Check local cache first
      const cachedOrder = orders.value.find((o) => o.clientOrderId === clientOrderId)
      if (cachedOrder) {
        return cachedOrder
      }

      // Fetch from server
      // 使用 DataService 获取订单详情
      const response = await dataService.getOrder({ origClientOrderId: clientOrderId })

      if (response) {
        // Update local cache (immutable update)
        const index = orders.value.findIndex((o) => o.clientOrderId === clientOrderId)
        if (index !== -1) {
          orders.value = orders.value.map((o, i) => (i === index ? response : o))
        } else {
          orders.value = [...orders.value, response]
        }
        lastUpdate.value = new Date()
        return response
      }

      return null
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch order'
      return null
    } finally {
      isLoading.value = false
    }
  }

  async function fetchOrders(filters?: OrderFilters): Promise<OrderListResponse> {
    isLoading.value = true
    error.value = null

    try {
      // 使用 DataService 获取订单列表
      const response = await dataService.listOrders(filters)

      // Update local cache
      orders.value = response.orders
      lastUpdate.value = new Date()

      return { orders: response.orders, count: response.count }
    } catch (e) {
      log('error', 'Failed to fetch orders:', e)
      error.value = e instanceof Error ? e.message : 'Failed to fetch orders'
      return { orders: [], count: 0 }
    } finally {
      isLoading.value = false
    }
  }

  async function fetchOpenOrders(symbol?: string): Promise<Order[]> {
    isLoading.value = true
    error.value = null

    try {
      // 使用 DataService 获取挂单列表
      const response = await dataService.getOpenOrders(symbol)

      // Update local cache
      openOrders.value = response.orders
      lastUpdate.value = new Date()

      return response.orders
    } catch (e) {
      log('error', 'Failed to fetch open orders:', e)
      error.value = e instanceof Error ? e.message : 'Failed to fetch open orders'
      return []
    } finally {
      isLoading.value = false
    }
  }

  async function cancelOrder(clientOrderId: string): Promise<Order | null> {
    isLoading.value = true
    error.value = null

    try {
      // Optimistic update
      const index = orders.value.findIndex((o) => o.clientOrderId === clientOrderId)
      if (index === -1) {
        throw new Error('Order not found')
      }

      // 获取订单的 symbol
      const order = orders.value[index]
      if (!order) {
        throw new Error('Order not found')
      }

      // 使用 DataService 取消订单
      const response = await dataService.cancelOrder({
        symbol: order.symbol,
        origClientOrderId: clientOrderId,
      })

      // Update order status (immutable update)
      const orderIndex = orders.value.findIndex((o) => o.clientOrderId === clientOrderId)
      if (orderIndex !== -1) {
        orders.value = orders.value.map((o, i) => (i === orderIndex ? response : o))

        // Remove from open orders (immutable update)
        openOrders.value = openOrders.value.filter((o) => o.clientOrderId !== clientOrderId)
      }

      lastUpdate.value = new Date()
      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to cancel order'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function setCurrentOrder(order: Order | null): void {
    currentOrder.value = order
  }

  function handleOrderUpdate(update: OrderUpdate): void {
    // Find and update existing order
    const index = orders.value.findIndex((o) => o.clientOrderId === update.clientOrderId)

    if (index !== -1) {
      // Update existing order (immutable update)
      orders.value = orders.value.map((o, i) =>
        i === index
          ? { ...o, status: update.status, data: update.data, updatedAt: update.updatedAt }
          : o
      )

      // Update open orders status or remove (immutable update)
      const openIndex = openOrders.value.findIndex(
        (o) => o.clientOrderId === update.clientOrderId
      )
      if (openIndex !== -1) {
        // Remove from open orders if not NEW or PARTIALLY_FILLED
        if (update.status !== 'NEW' && update.status !== 'PARTIALLY_FILLED') {
          openOrders.value = openOrders.value.filter((o) => o.clientOrderId !== update.clientOrderId)
        } else {
          // Update the status in openOrders
          openOrders.value = openOrders.value.map((o, i) =>
            i === openIndex
              ? { ...o, status: update.status, data: update.data, updatedAt: update.updatedAt }
              : o
          )
        }
      }
    } else {
      // Add new order (from WebSocket push)
      // 市场类型通过 symbol 区分：.PERP 结尾为期货
      const newOrder: Order = {
        clientOrderId: update.clientOrderId,
        binanceOrderId: update.binanceOrderId,
        symbol: update.symbol,
        side: update.side,
        orderType: update.orderType,
        status: update.status,
        data: update.data,
        createdAt: update.updatedAt,
        updatedAt: update.updatedAt,
      }
      orders.value = [...orders.value, newOrder]
    }

    // Update current order if it's the same order
    if (currentOrder.value?.clientOrderId === update.clientOrderId) {
      currentOrder.value = orders.value[index !== -1 ? index : orders.value.length - 1]
    }

    lastUpdate.value = new Date()
  }

  function clearError(): void {
    error.value = null
  }

  return {
    // State
    orders,
    openOrders,
    currentOrder,
    isLoading,
    error,
    lastUpdate,

    // Computed
    hasOpenOrders,
    ordersByMarket,

    // Actions
    createOrder,
    fetchOrder,
    fetchOrders,
    fetchOpenOrders,
    cancelOrder,
    setCurrentOrder,
    handleOrderUpdate,
    clearError,
  }
})
