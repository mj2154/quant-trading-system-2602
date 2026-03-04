import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Order,
  CreateOrderParams,
  OrderFilters,
  OrderUpdate,
  OrderListResponse,
  MarketType,
  TradingMessage,
} from '../types/trading-types'

// Development mode flag
const isDev = import.meta.env.DEV

// Logger utility
function log(level: 'log' | 'error', message: string, ...args: unknown[]) {
  if (level === 'error' || isDev) {
    console[level](`[TradingStore] ${message}`, ...args)
  }
}

// Generate unique client order ID
function generateClientOrderId(): string {
  return `ord_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`
}

// WebSocket connection management
let wsConnection: WebSocket | null = null
const messageHandlers = new Map<string, (data: unknown) => void>()

function getWebSocketUrl(): string {
  // Get WebSocket URL from environment - fail if not configured in production
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_WS_HOST
  if (!host) {
    if (isDev) {
      log('log', 'VITE_WS_HOST not set, using localhost:8000 for development')
      return `${wsProtocol}//localhost:8000/ws/trading`
    }
    throw new Error('VITE_WS_HOST environment variable is required')
  }
  return `${wsProtocol}//${host}/ws/trading`
}

function connectWebSocket(): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      resolve(wsConnection)
      return
    }

    try {
      wsConnection = new WebSocket(getWebSocketUrl())

      wsConnection.onopen = () => {
        log('log', 'WebSocket connected')
        resolve(wsConnection!)
      }

      wsConnection.onerror = (error) => {
        log('error', 'WebSocket error:', error)
        reject(error)
      }

      wsConnection.onclose = () => {
        log('log', 'WebSocket closed')
        wsConnection = null
      }

      wsConnection.onmessage = (event) => {
        try {
          const message: TradingMessage = JSON.parse(event.data)
          const handler = messageHandlers.get(message.type)
          if (handler) {
            handler(message.data)
          }
        } catch (e) {
          log('error', 'Failed to parse message:', e)
        }
      }
    } catch (error) {
      reject(error)
    }
  })
}

function sendMessage<T>(type: string, data?: unknown): Promise<T> {
  return new Promise(async (resolve, reject) => {
    try {
      const ws = await connectWebSocket()
      const correlationId = generateClientOrderId()

      // Set up one-time handler for response
      messageHandlers.set(correlationId, (responseData) => {
        messageHandlers.delete(correlationId)
        resolve(responseData as T)
      })

      const message = {
        type,
        correlationId,
        data,
      }

      ws.send(JSON.stringify(message))

      // Timeout after 30 seconds
      setTimeout(() => {
        if (messageHandlers.has(correlationId)) {
          messageHandlers.delete(correlationId)
          reject(new Error(`Request ${type} timed out`))
        }
      }, 30000)
    } catch (error) {
      reject(error)
    }
  })
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

  const ordersByMarket = computed(() => {
    const result: Record<MarketType, Order[]> = {
      FUTURES: [],
      SPOT: [],
    }
    orders.value.forEach((order) => {
      result[order.marketType].push(order)
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
      if (params.orderType === 'MARKET') {
        if (params.marketType === 'SPOT') {
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
        (params.orderType === 'LIMIT' || params.orderType === 'STOP_LOSS_LIMIT' || params.orderType === 'TAKE_PROFIT_LIMIT') &&
        !params.price &&
        !params.priceMatch  // priceMatch can replace price
      ) {
        throw new Error('Price is required for limit orders')
      }

      // Validate stopPrice for stop orders
      if (
        (params.orderType === 'STOP' || params.orderType === 'STOP_LOSS' || params.orderType === 'STOP_LOSS_LIMIT' || params.orderType === 'TAKE_PROFIT' || params.orderType === 'TAKE_PROFIT_LIMIT') &&
        !params.stopPrice &&
        !params.trailingDelta  // trailingDelta can replace stopPrice
      ) {
        throw new Error('Stop price or trailingDelta is required for stop orders')
      }

      // Validate trailingDelta for TRAILING_STOP_MARKET
      if (params.orderType === 'TRAILING_STOP_MARKET' && !params.trailingDelta) {
        throw new Error('TrailingDelta is required for trailing stop orders')
      }

      // Validate goodTillDate for GTD orders
      if (params.timeInForce === 'GTD' && !params.goodTillDate) {
        throw new Error('goodTillDate is required for GTD orders')
      }

      const clientOrderId = generateClientOrderId()

      // Create order locally first (optimistic update)
      const newOrder: Order = {
        clientOrderId,
        marketType: params.marketType,
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
        const response = await sendMessage<Order>('CREATE_ORDER', {
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
      const response = await sendMessage<Order>('GET_ORDER', { clientOrderId })

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
      // Fetch from server
      const response = await sendMessage<OrderListResponse>('LIST_ORDERS', filters || {})

      // Update local cache
      orders.value = response.orders
      lastUpdate.value = new Date()

      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch orders'
      return { orders: [], count: 0 }
    } finally {
      isLoading.value = false
    }
  }

  async function fetchOpenOrders(marketType?: MarketType): Promise<Order[]> {
    isLoading.value = true
    error.value = null

    try {
      // Fetch from server
      const response = await sendMessage<Order[]>('GET_OPEN_ORDERS', { marketType })

      // Update local cache
      openOrders.value = response
      lastUpdate.value = new Date()

      return response
    } catch (e) {
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

      // Send cancel request to server
      const response = await sendMessage<Order>('CANCEL_ORDER', { clientOrderId })

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
      const newOrder: Order = {
        clientOrderId: update.clientOrderId,
        binanceOrderId: update.binanceOrderId,
        marketType: update.marketType,
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
