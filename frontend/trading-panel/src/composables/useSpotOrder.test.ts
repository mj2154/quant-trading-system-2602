/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.OPEN
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onerror: ((error: Event) => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null

  constructor(public url: string) {
    setTimeout(() => this.onopen?.(), 0)
  }

  send(data: string) {
    const message = JSON.parse(data)
    // Simulate server response
    setTimeout(() => {
      if (this.onmessage) {
        let response: Record<string, unknown>

        if (message.type === 'CREATE_ORDER') {
          response = {
            type: 'ORDER_DATA',
            requestId: message.requestId,
            data: {
              clientOrderId: message.data?.newClientOrderId || message.data?.clientOrderId || 'test-order-id',
              symbol: message.data?.symbol,
              side: message.data?.side,
              orderType: message.data?.type,
              status: 'NEW',
              marketType: 'SPOT',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              data: message.data,
            },
          }
        } else if (message.type === 'LIST_ORDERS') {
          response = {
            type: 'ORDER_LIST_DATA',
            requestId: message.requestId,
            data: {
              orders: [
                {
                  clientOrderId: 'order-1',
                  symbol: message.data?.symbol,
                  side: 'BUY',
                  orderType: 'LIMIT',
                  status: 'FILLED',
                  marketType: 'SPOT',
                  createdAt: new Date().toISOString(),
                  updatedAt: new Date().toISOString(),
                  data: {},
                },
              ],
              count: 1,
            },
          }
        } else {
          response = {
            type: `${message.type}_RESPONSE`,
            requestId: message.requestId,
            data: {
              clientOrderId: message.data?.newClientOrderId || message.data?.clientOrderId || 'test-order-id',
              symbol: message.data?.symbol,
              side: message.data?.side,
              orderType: message.data?.type,
              status: 'NEW',
              marketType: 'SPOT',
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              data: message.data,
            },
          }
        }
        this.onmessage({ data: JSON.stringify(response) })
      }
    }, 10)
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.()
  }
}

// Mock crypto.randomUUID
const mockUuid = '550e8400e29b41d4a716446655440000'
vi.stubGlobal('crypto', {
  randomUUID: vi.fn().mockReturnValue(mockUuid),
})

// Import module after mocking globals
// eslint-disable-next-line import/order
import { useSpotOrder } from './useSpotOrder'

describe('useSpotOrder', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('createSpotOrder', () => {
    it('should create a spot LIMIT order with correct parameters', async () => {
      const { createSpotOrder } = useSpotOrder()

      const order = await createSpotOrder({
        symbol: 'BTCUSDT',
        side: 'BUY',
        type: 'LIMIT',
        quantity: 0.001,
        price: 50000,
        timeInForce: 'GTC',
      })

      expect(order).toBeDefined()
      expect(order.symbol).toBe('BINANCE:BTCUSDT')
      expect(order.side).toBe('BUY')
      expect(order.orderType).toBe('LIMIT')
    })

    it('should create a spot MARKET order with quoteOrderQty', async () => {
      const { createSpotOrder } = useSpotOrder()

      const order = await createSpotOrder({
        symbol: 'ETHUSDT',
        side: 'SELL',
        type: 'MARKET',
        quoteOrderQty: 1000,
      })

      expect(order).toBeDefined()
      expect(order.symbol).toBe('BINANCE:ETHUSDT')
      expect(order.side).toBe('SELL')
      expect(order.orderType).toBe('MARKET')
    })

    it('should create a STOP_LOSS order with stopPrice', async () => {
      const { createSpotOrder } = useSpotOrder()

      const order = await createSpotOrder({
        symbol: 'BTCUSDT',
        side: 'SELL',
        type: 'STOP_LOSS',
        quantity: 0.001,
        stopPrice: 45000,
      })

      expect(order).toBeDefined()
      expect(order.orderType).toBe('STOP_LOSS')
    })

    it('should create order with icebergQty for LIMIT order', async () => {
      const { createSpotOrder } = useSpotOrder()

      const order = await createSpotOrder({
        symbol: 'BTCUSDT',
        side: 'BUY',
        type: 'LIMIT',
        quantity: 1.0,
        price: 50000,
        icebergQty: 0.1,
      })

      expect(order).toBeDefined()
    })

    it('should create order with trailingDelta for STOP_LOSS_LIMIT', async () => {
      const { createSpotOrder } = useSpotOrder()

      const order = await createSpotOrder({
        symbol: 'BTCUSDT',
        side: 'SELL',
        type: 'STOP_LOSS_LIMIT',
        quantity: 0.5,
        price: 48000,
        stopPrice: 45000,
        trailingDelta: 100,
      })

      expect(order).toBeDefined()
    })

    it('should create order with strategy parameters', async () => {
      const { createSpotOrder } = useSpotOrder()

      const order = await createSpotOrder({
        symbol: 'BTCUSDT',
        side: 'BUY',
        type: 'LIMIT',
        quantity: 0.1,
        price: 50000,
        strategyId: 12345,
        strategyType: 1000000,
      })

      expect(order).toBeDefined()
    })

    it('should create LIMIT_MAKER order', async () => {
      const { createSpotOrder } = useSpotOrder()

      const order = await createSpotOrder({
        symbol: 'BTCUSDT',
        side: 'BUY',
        type: 'LIMIT_MAKER',
        quantity: 0.001,
        price: 50000,
      })

      expect(order).toBeDefined()
      expect(order.orderType).toBe('LIMIT_MAKER')
    })

    it('should throw error when LIMIT order missing price', async () => {
      const { createSpotOrder } = useSpotOrder()

      await expect(
        createSpotOrder({
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'LIMIT',
          quantity: 0.001,
        })
      ).rejects.toThrow('Price is required for LIMIT order')
    })

    it('should throw error when STOP_LOSS order missing stopPrice', async () => {
      const { createSpotOrder } = useSpotOrder()

      await expect(
        createSpotOrder({
          symbol: 'BTCUSDT',
          side: 'SELL',
          type: 'STOP_LOSS',
          quantity: 0.001,
        })
      ).rejects.toThrow('Stop price is required for STOP_LOSS order')
    })

    it('should throw error when MARKET order missing quantity and quoteOrderQty', async () => {
      const { createSpotOrder } = useSpotOrder()

      await expect(
        createSpotOrder({
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'MARKET',
        })
      ).rejects.toThrow('Quantity or quoteOrderQty is required for MARKET order')
    })
  })

  describe('getOrder', () => {
    it('should fetch order by origClientOrderId', async () => {
      const { getOrder } = useSpotOrder()

      const order = await getOrder('BTCUSDT', undefined, 'test-client-order-id')

      expect(order).toBeDefined()
    })

    it('should fetch order by orderId', async () => {
      const { getOrder } = useSpotOrder()

      const order = await getOrder('BTCUSDT', 123456789)

      expect(order).toBeDefined()
    })
  })

  describe('cancelOrder', () => {
    it('should cancel order by origClientOrderId', async () => {
      const { cancelOrder } = useSpotOrder()

      const result = await cancelOrder('BTCUSDT', undefined, 'test-client-order-id')

      expect(result).toBeDefined()
    })

    it('should cancel order by orderId', async () => {
      const { cancelOrder } = useSpotOrder()

      const result = await cancelOrder('BTCUSDT', 123456789)

      expect(result).toBeDefined()
    })
  })

  describe('listOrders', () => {
    it('should list orders with filters', async () => {
      const { listOrders } = useSpotOrder()

      const result = await listOrders({
        symbol: 'BTCUSDT',
        limit: 100,
      })

      expect(result).toBeDefined()
      expect(result.orders).toBeDefined()
    })

    it('should list orders with time range', async () => {
      const { listOrders } = useSpotOrder()

      const result = await listOrders({
        symbol: 'BTCUSDT',
        startTime: Date.now() - 86400000,
        endTime: Date.now(),
      })

      expect(result).toBeDefined()
    })
  })

  describe('getOpenOrders', () => {
    it('should get all open orders', async () => {
      const { getOpenOrders } = useSpotOrder()

      const orders = await getOpenOrders()

      expect(orders).toBeDefined()
    })

    it('should get open orders for specific symbol', async () => {
      const { getOpenOrders } = useSpotOrder()

      const orders = await getOpenOrders('BTCUSDT')

      expect(orders).toBeDefined()
    })
  })

  describe('generateClientOrderId', () => {
    it('should generate UUID v4 hex format', () => {
      const { generateClientOrderId } = useSpotOrder()

      const id = generateClientOrderId()

      expect(id).toHaveLength(32)
      expect(id).toMatch(/^[0-9a-f]{32}$/)
    })
  })

  describe('formatSymbolForSpot', () => {
    it('should add BINANCE: prefix for spot', () => {
      const { formatSymbolForSpot } = useSpotOrder()

      expect(formatSymbolForSpot('BTCUSDT')).toBe('BINANCE:BTCUSDT')
    })

    it('should not add prefix if already has BINANCE:', () => {
      const { formatSymbolForSpot } = useSpotOrder()

      expect(formatSymbolForSpot('BINANCE:BTCUSDT')).toBe('BINANCE:BTCUSDT')
    })
  })
})
