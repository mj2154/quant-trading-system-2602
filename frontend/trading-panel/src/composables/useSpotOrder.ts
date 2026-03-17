/**
 * useSpotOrder - Composable for spot order operations
 * Based on design document: docs/frontend/design/SPOT_TRADING_PAGE_DESIGN.md
 *
 * 使用 DataService 统一管理 WebSocket 连接
 */

import { ref } from 'vue'
import { dataService } from '../services/data-service/DataService'
import type { Order, OrderListResponse, SpotOrderType, OrderTimeInForce } from '../types/api'

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

      // 使用 DataService 创建订单
      const order = await dataService.createOrder({
        symbol: formatSymbolForSpot(params.symbol),
        side: params.side,
        orderType: params.type,
        clientOrderId: newClientOrderId,
        quantity: params.quantity?.toString(),
        quoteOrderQty: params.quoteOrderQty?.toString(),
        price: params.price?.toString(),
        stopPrice: params.stopPrice?.toString(),
        timeInForce: params.timeInForce,
        icebergQty: params.icebergQty?.toString(),
        trailingDelta: params.trailingDelta,
        strategyId: params.strategyId,
        strategyType: params.strategyType,
        selfTradePreventionMode: params.selfTradePreventionMode,
      })

      return order
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
      // 使用 DataService 获取订单
      const order = await dataService.getOrder({
        symbol: formatSymbolForSpot(symbol),
        orderId,
        origClientOrderId,
      })
      return order
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
      // 使用 DataService 取消订单
      const order = await dataService.cancelOrder({
        symbol: formatSymbolForSpot(symbol),
        orderId,
        origClientOrderId,
      })
      return order
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
      // 使用 DataService 获取订单列表
      const response = await dataService.listOrders({
        symbol: formatSymbolForSpot(params.symbol),
        startTime: params.startTime,
        endTime: params.endTime,
        limit: params.limit,
        status: params.status,
      })
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
      // 使用 DataService 获取挂单列表
      const response = await dataService.getOpenOrders(symbol ? formatSymbolForSpot(symbol) : undefined)
      return response.orders
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
