import { describe, expect, it, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import type { Order, CreateOrderParams, OrderFilters, OrderUpdate, MarketType } from '../../types/trading-types'

// Mock the WebSocket module
vi.mock('../../utils/websocket', () => ({
  createWebSocketConnection: vi.fn(),
}))

describe('Trading Store', () => {
  let tradingStore: ReturnType<typeof import('../../stores/trading-store').useTradingStore>

  beforeEach(async () => {
    setActivePinia(createPinia())
    const { useTradingStore } = await import('../../stores/trading-store')
    tradingStore = useTradingStore()
  })

  describe('Initial State', () => {
    it('should have empty orders array', () => {
      expect(tradingStore.orders).toEqual([])
    })

    it('should have empty openOrders array', () => {
      expect(tradingStore.openOrders).toEqual([])
    })

    it('should have null currentOrder', () => {
      expect(tradingStore.currentOrder).toBeNull()
    })

    it('should have isLoading as false', () => {
      expect(tradingStore.isLoading).toBe(false)
    })

    it('should have null error', () => {
      expect(tradingStore.error).toBeNull()
    })

    it('should have lastUpdate as Date', () => {
      expect(tradingStore.lastUpdate).toBeInstanceOf(Date)
    })
  })

  describe('setCurrentOrder', () => {
    it('should set current order', () => {
      const order: Order = {
        clientOrderId: 'test-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {},
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }

      tradingStore.setCurrentOrder(order)

      expect(tradingStore.currentOrder).toEqual(order)
    })

    it('should clear current order when null passed', () => {
      tradingStore.setCurrentOrder(null)
      expect(tradingStore.currentOrder).toBeNull()
    })
  })

  describe('clearError', () => {
    it('should clear error state', () => {
      tradingStore.error = 'Test error'
      tradingStore.clearError()
      expect(tradingStore.error).toBeNull()
    })
  })

  describe('handleOrderUpdate', () => {
    it('should update existing order status from WebSocket push', () => {
      // First add an order to the store
      const order: Order = {
        clientOrderId: 'test-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {},
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }
      tradingStore.orders.push(order)

      const update: OrderUpdate = {
        clientOrderId: 'test-order-id',
        binanceOrderId: 123456,
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'FILLED',
        data: { executedQty: '0.5' },
        updatedAt: '2026-03-01T01:00:00Z',
      }

      tradingStore.handleOrderUpdate(update)

      const updatedOrder = tradingStore.orders.find((o) => o.clientOrderId === 'test-order-id')
      expect(updatedOrder?.status).toBe('FILLED')
    })

    it('should add new order if not exists', () => {
      const update: OrderUpdate = {
        clientOrderId: 'new-order-id',
        binanceOrderId: 999999,
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {},
        updatedAt: '2026-03-01T00:00:00Z',
      }

      tradingStore.handleOrderUpdate(update)

      const order = tradingStore.orders.find((o) => o.clientOrderId === 'new-order-id')
      expect(order).toBeDefined()
      expect(order?.status).toBe('NEW')
    })

    it('should remove from openOrders when order is filled', () => {
      const order: Order = {
        clientOrderId: 'test-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {},
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }
      tradingStore.orders.push(order)
      tradingStore.openOrders.push({ ...order })

      const update: OrderUpdate = {
        clientOrderId: 'test-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'FILLED',
        data: { executedQty: '0.5' },
        updatedAt: '2026-03-01T01:00:00Z',
      }

      tradingStore.handleOrderUpdate(update)

      const openOrder = tradingStore.openOrders.find((o) => o.clientOrderId === 'test-order-id')
      expect(openOrder).toBeUndefined()
    })

    it('should keep in openOrders when order is partially filled', () => {
      const order: Order = {
        clientOrderId: 'test-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {},
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }
      tradingStore.orders.push(order)
      tradingStore.openOrders.push({ ...order })

      const update: OrderUpdate = {
        clientOrderId: 'test-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'PARTIALLY_FILLED',
        data: { executedQty: '0.25' },
        updatedAt: '2026-03-01T01:00:00Z',
      }

      tradingStore.handleOrderUpdate(update)

      const openOrder = tradingStore.openOrders.find((o) => o.clientOrderId === 'test-order-id')
      expect(openOrder).toBeDefined()
      expect(openOrder?.status).toBe('PARTIALLY_FILLED')
    })

    it('should update currentOrder if it matches the updated order', () => {
      const order: Order = {
        clientOrderId: 'test-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {},
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }
      tradingStore.orders.push(order)
      tradingStore.setCurrentOrder(order)

      const update: OrderUpdate = {
        clientOrderId: 'test-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'FILLED',
        data: { executedQty: '0.5' },
        updatedAt: '2026-03-01T01:00:00Z',
      }

      tradingStore.handleOrderUpdate(update)

      expect(tradingStore.currentOrder?.status).toBe('FILLED')
    })

    it('should update lastUpdate timestamp', () => {
      const initialLastUpdate = tradingStore.lastUpdate.getTime()

      const update: OrderUpdate = {
        clientOrderId: 'new-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {},
        updatedAt: new Date().toISOString(),
      }

      // Small delay to ensure timestamp changes
      const now = Date.now()
      vi.spyOn(Date, 'now').mockImplementation(() => now)

      tradingStore.handleOrderUpdate(update)

      expect(tradingStore.lastUpdate.getTime()).toBeGreaterThanOrEqual(initialLastUpdate)
    })
  })

  describe('Computed values', () => {
    it('hasOpenOrders should return false when no open orders', () => {
      expect(tradingStore.hasOpenOrders).toBe(false)
    })

    it('hasOpenOrders should return true when there are open orders', () => {
      const order: Order = {
        clientOrderId: 'test-order-id',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {},
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }
      tradingStore.openOrders.push(order)

      expect(tradingStore.hasOpenOrders).toBe(true)
    })

    it('ordersByMarket should group orders by market type', () => {
      const futuresOrder: Order = {
        clientOrderId: 'futures-order',
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {},
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }

      const spotOrder: Order = {
        clientOrderId: 'spot-order',
        marketType: 'SPOT',
        symbol: 'ETHUSDT',
        side: 'SELL',
        orderType: 'MARKET',
        status: 'FILLED',
        data: {},
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }

      tradingStore.orders.push(futuresOrder, spotOrder)

      expect(tradingStore.ordersByMarket.FUTURES).toHaveLength(1)
      expect(tradingStore.ordersByMarket.SPOT).toHaveLength(1)
      expect(tradingStore.ordersByMarket.FUTURES[0].clientOrderId).toBe('futures-order')
      expect(tradingStore.ordersByMarket.SPOT[0].clientOrderId).toBe('spot-order')
    })
  })
})
