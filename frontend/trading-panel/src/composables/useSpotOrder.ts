/**
 * useSpotOrder - Composable for spot order operations
 * Based on design document: docs/frontend/design/SPOT_TRADING_PAGE_DESIGN.md
 */

import { ref } from 'vue'
import type { Order, OrderListResponse, SpotOrderType, OrderTimeInForce } from '../types/api'

// ID generation functions (must follow UUID v4 hex format - 32 characters)
function generateRequestId(): string {
  return crypto.randomUUID().replace(/-/g, '')
}

function generateClientOrderId(): string {
  return crypto.randomUUID().replace(/-/g, '')
}

// WebSocket connection management
let wsConnection: WebSocket | null = null
const messageHandlers = new Map<string, (data: unknown) => void>()

function getWebSocketUrl(): string {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_WS_HOST || 'localhost:8000'
  return `${wsProtocol}//${host}/ws`
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
        resolve(wsConnection!)
      }

      wsConnection.onerror = (error) => {
        reject(error)
      }

      wsConnection.onclose = () => {
        wsConnection = null
      }

      wsConnection.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          const requestId = message.requestId
          if (requestId && messageHandlers.has(requestId)) {
            const handler = messageHandlers.get(requestId)
            if (handler) {
              handler(message.data)
            }
          }
        } catch (e) {
          console.error('[useSpotOrder] Failed to parse message:', e)
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
      const requestId = generateRequestId()

      messageHandlers.set(requestId, (responseData) => {
        messageHandlers.delete(requestId)
        resolve(responseData as T)
      })

      const message = {
        protocolVersion: '2.0',
        type,
        requestId,
        timestamp: Date.now(),
        data,
      }

      ws.send(JSON.stringify(message))

      // Timeout after 30 seconds
      setTimeout(() => {
        if (messageHandlers.has(requestId)) {
          messageHandlers.delete(requestId)
          reject(new Error(`Request ${type} timed out`))
        }
      }, 30000)
    } catch (error) {
      reject(error)
    }
  })
}

// Create spot order params (使用统一的 types/api 定义)
export interface CreateSpotOrderParams {
  symbol: string
  side: 'BUY' | 'SELL'
  type: SpotOrderType
  quantity?: number
  quoteOrderQty?: number
  price?: number
  stopPrice?: number
  timeInForce?: OrderTimeInForce
  icebergQty?: number
  trailingDelta?: number
  strategyId?: number
  strategyType?: number
  selfTradePreventionMode?: string
  newOrderRespType?: 'ACK' | 'RESULT' | 'FULL'
}

// List orders params
export interface ListOrdersParams {
  symbol: string
  startTime?: number
  endTime?: number
  limit?: number
  status?: string
}

export function useSpotOrder() {
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Format symbol for spot trading (add BINANCE: prefix)
   */
  function formatSymbolForSpot(symbol: string): string {
    if (symbol.startsWith('BINANCE:')) {
      return symbol
    }
    return `BINANCE:${symbol}`
  }

  /**
   * Generate client order ID (UUID v4 hex format)
   */
  function generateClientOrderId(): string {
    return crypto.randomUUID().replace(/-/g, '')
  }

  /**
   * Validate order parameters before creating
   */
  function validateOrderParams(params: CreateSpotOrderParams): void {
    // Validate symbol
    if (!params.symbol) {
      throw new Error('Symbol is required')
    }

    // Validate side
    if (!params.side || !['BUY', 'SELL'].includes(params.side)) {
      throw new Error('Side must be BUY or SELL')
    }

    // Validate order type
    const validTypes: SpotOrderType[] = [
      'LIMIT',
      'MARKET',
      'STOP_LOSS',
      'STOP_LOSS_LIMIT',
      'TAKE_PROFIT',
      'TAKE_PROFIT_LIMIT',
      'LIMIT_MAKER',
    ]
    if (!params.type || !validTypes.includes(params.type)) {
      throw new Error('Invalid order type')
    }

    // Validate quantity for MARKET orders
    if (params.type === 'MARKET') {
      if (!params.quantity && !params.quoteOrderQty) {
        throw new Error('Quantity or quoteOrderQty is required for MARKET order')
      }
    } else {
      if (!params.quantity) {
        throw new Error('Quantity is required')
      }
    }

    // Validate price for limit orders
    if (
      (params.type === 'LIMIT' ||
        params.type === 'STOP_LOSS_LIMIT' ||
        params.type === 'TAKE_PROFIT_LIMIT' ||
        params.type === 'LIMIT_MAKER') &&
      !params.price
    ) {
      throw new Error(`Price is required for ${params.type} order`)
    }

    // Validate stopPrice for stop orders
    if (
      (params.type === 'STOP_LOSS' ||
        params.type === 'STOP_LOSS_LIMIT' ||
        params.type === 'TAKE_PROFIT' ||
        params.type === 'TAKE_PROFIT_LIMIT') &&
      !params.stopPrice &&
      !params.trailingDelta
    ) {
      throw new Error(`Stop price is required for ${params.type} order`)
    }
  }

  /**
   * Create a spot order
   */
  async function createSpotOrder(params: CreateSpotOrderParams): Promise<Order> {
    isLoading.value = true
    error.value = null

    try {
      // Validate parameters
      validateOrderParams(params)

      // Generate client order ID
      const newClientOrderId = generateClientOrderId()

      // Build order data with BINANCE: prefix for symbol
      const orderData: Record<string, unknown> = {
        symbol: formatSymbolForSpot(params.symbol),
        side: params.side,
        type: params.type,
        newClientOrderId,
      }

      // Add optional parameters conditionally
      if (params.quantity !== undefined) {
        orderData.quantity = params.quantity
      }
      if (params.quoteOrderQty !== undefined) {
        orderData.quoteOrderQty = params.quoteOrderQty
      }
      if (params.price !== undefined) {
        orderData.price = params.price
      }
      if (params.stopPrice !== undefined) {
        orderData.stopPrice = params.stopPrice
      }
      if (params.timeInForce !== undefined) {
        orderData.timeInForce = params.timeInForce
      }
      if (params.icebergQty !== undefined) {
        orderData.icebergQty = params.icebergQty
      }
      if (params.trailingDelta !== undefined) {
        orderData.trailingDelta = params.trailingDelta
      }
      if (params.strategyId !== undefined) {
        orderData.strategyId = params.strategyId
      }
      if (params.strategyType !== undefined) {
        orderData.strategyType = params.strategyType
      }
      if (params.selfTradePreventionMode !== undefined) {
        orderData.selfTradePreventionMode = params.selfTradePreventionMode
      }
      if (params.newOrderRespType !== undefined) {
        orderData.newOrderRespType = params.newOrderRespType
      }

      // Send request
      const response = await sendMessage<Order>('CREATE_ORDER', orderData)
      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create order'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get order by orderId or origClientOrderId
   */
  async function getOrder(
    symbol: string,
    orderId?: number,
    origClientOrderId?: string
  ): Promise<Order | null> {
    isLoading.value = true
    error.value = null

    try {
      const data: Record<string, unknown> = { symbol: formatSymbolForSpot(symbol) }

      if (orderId) {
        data.orderId = orderId
      } else if (origClientOrderId) {
        data.origClientOrderId = origClientOrderId
      }

      const response = await sendMessage<Order>('GET_ORDER', data)
      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to get order'
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Cancel order by orderId or origClientOrderId
   */
  async function cancelOrder(
    symbol: string,
    orderId?: number,
    origClientOrderId?: string
  ): Promise<Order | null> {
    isLoading.value = true
    error.value = null

    try {
      const data: Record<string, unknown> = { symbol: formatSymbolForSpot(symbol) }

      if (orderId) {
        data.orderId = orderId
      } else if (origClientOrderId) {
        data.origClientOrderId = origClientOrderId
      }

      const response = await sendMessage<Order>('CANCEL_ORDER', data)
      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to cancel order'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  /**
   * List orders with filters
   */
  async function listOrders(params: ListOrdersParams): Promise<OrderListResponse> {
    isLoading.value = true
    error.value = null

    try {
      const requestData = {
        ...params,
        symbol: formatSymbolForSpot(params.symbol),
      }

      const response = await sendMessage<OrderListResponse>('LIST_ORDERS', requestData)
      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to list orders'
      return { orders: [], count: 0 }
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get open orders
   */
  async function getOpenOrders(symbol?: string): Promise<Order[]> {
    isLoading.value = true
    error.value = null

    try {
      const data = symbol ? { symbol: formatSymbolForSpot(symbol) } : {}
      const response = await sendMessage<Order[]>('GET_OPEN_ORDERS', data)

      // Handle response format
      const responseData = response as { orders?: Order[] } | undefined
      return responseData?.orders || response || []
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to get open orders'
      return []
    } finally {
      isLoading.value = false
    }
  }

  return {
    // State
    isLoading,
    error,

    // Actions
    createSpotOrder,
    getOrder,
    cancelOrder,
    listOrders,
    getOpenOrders,

    // Utilities
    generateClientOrderId,
    formatSymbolForSpot,
  }
}
