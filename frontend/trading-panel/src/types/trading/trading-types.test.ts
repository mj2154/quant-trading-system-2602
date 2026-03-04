import { describe, expect, it } from 'vitest'
import type {
  MarketType,
  OrderSide,
  OrderType,
  PositionSide,
  TimeInForce,
  OrderStatus,
  CreateOrderParams,
  Order,
  OrderListResponse,
  OrderUpdate,
} from '../trading-types'

describe('Trading Types', () => {
  // Test MarketType
  describe('MarketType', () => {
    it('should accept FUTURES as valid market type', () => {
      const marketType: MarketType = 'FUTURES'
      expect(marketType).toBe('FUTURES')
    })

    it('should accept SPOT as valid market type', () => {
      const marketType: MarketType = 'SPOT'
      expect(marketType).toBe('SPOT')
    })
  })

  // Test OrderSide
  describe('OrderSide', () => {
    it('should accept BUY as valid order side', () => {
      const side: OrderSide = 'BUY'
      expect(side).toBe('BUY')
    })

    it('should accept SELL as valid order side', () => {
      const side: OrderSide = 'SELL'
      expect(side).toBe('SELL')
    })
  })

  // Test OrderType
  describe('OrderType', () => {
    it('should accept LIMIT order type', () => {
      const orderType: OrderType = 'LIMIT'
      expect(orderType).toBe('LIMIT')
    })

    it('should accept MARKET order type', () => {
      const orderType: OrderType = 'MARKET'
      expect(orderType).toBe('MARKET')
    })

    it('should accept STOP order type', () => {
      const orderType: OrderType = 'STOP'
      expect(orderType).toBe('STOP')
    })

    it('should accept STOP_LOSS order type', () => {
      const orderType: OrderType = 'STOP_LOSS'
      expect(orderType).toBe('STOP_LOSS')
    })

    it('should accept TAKE_PROFIT order type', () => {
      const orderType: OrderType = 'TAKE_PROFIT'
      expect(orderType).toBe('TAKE_PROFIT')
    })
  })

  // Test PositionSide
  describe('PositionSide', () => {
    it('should accept BOTH position side', () => {
      const positionSide: PositionSide = 'BOTH'
      expect(positionSide).toBe('BOTH')
    })

    it('should accept LONG position side', () => {
      const positionSide: PositionSide = 'LONG'
      expect(positionSide).toBe('LONG')
    })

    it('should accept SHORT position side', () => {
      const positionSide: PositionSide = 'SHORT'
      expect(positionSide).toBe('SHORT')
    })
  })

  // Test TimeInForce
  describe('TimeInForce', () => {
    it('should accept GTC time in force', () => {
      const timeInForce: TimeInForce = 'GTC'
      expect(timeInForce).toBe('GTC')
    })

    it('should accept IOC time in force', () => {
      const timeInForce: TimeInForce = 'IOC'
      expect(timeInForce).toBe('IOC')
    })

    it('should accept FOK time in force', () => {
      const timeInForce: TimeInForce = 'FOK'
      expect(timeInForce).toBe('FOK')
    })

    it('should accept GTD time in force', () => {
      const timeInForce: TimeInForce = 'GTD'
      expect(timeInForce).toBe('GTD')
    })
  })

  // Test OrderStatus
  describe('OrderStatus', () => {
    it('should accept NEW status', () => {
      const status: OrderStatus = 'NEW'
      expect(status).toBe('NEW')
    })

    it('should accept FILLED status', () => {
      const status: OrderStatus = 'FILLED'
      expect(status).toBe('FILLED')
    })

    it('should accept PARTIALLY_FILLED status', () => {
      const status: OrderStatus = 'PARTIALLY_FILLED'
      expect(status).toBe('PARTIALLY_FILLED')
    })

    it('should accept CANCELED status', () => {
      const status: OrderStatus = 'CANCELED'
      expect(status).toBe('CANCELED')
    })

    it('should accept REJECTED status', () => {
      const status: OrderStatus = 'REJECTED'
      expect(status).toBe('REJECTED')
    })

    it('should accept EXPIRED status', () => {
      const status: OrderStatus = 'EXPIRED'
      expect(status).toBe('EXPIRED')
    })
  })

  // Test CreateOrderParams
  describe('CreateOrderParams', () => {
    it('should create valid order params for LIMIT order', () => {
      const params: CreateOrderParams = {
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        quantity: 0.5,
        price: 50000,
        timeInForce: 'GTC',
      }
      expect(params.marketType).toBe('FUTURES')
      expect(params.symbol).toBe('BTCUSDT')
      expect(params.side).toBe('BUY')
      expect(params.orderType).toBe('LIMIT')
      expect(params.quantity).toBe(0.5)
      expect(params.price).toBe(50000)
      expect(params.timeInForce).toBe('GTC')
    })

    it('should create valid order params for MARKET order without price', () => {
      const params: CreateOrderParams = {
        marketType: 'SPOT',
        symbol: 'ETHUSDT',
        side: 'SELL',
        orderType: 'MARKET',
        quantity: 1.0,
      }
      expect(params.orderType).toBe('MARKET')
      expect(params.price).toBeUndefined()
    })

    it('should create valid order params for STOP order', () => {
      const params: CreateOrderParams = {
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'SELL',
        orderType: 'STOP_LOSS',
        quantity: 0.1,
        stopPrice: 45000,
        reduceOnly: true,
        positionSide: 'SHORT',
      }
      expect(params.stopPrice).toBe(45000)
      expect(params.reduceOnly).toBe(true)
      expect(params.positionSide).toBe('SHORT')
    })
  })

  // Test Order
  describe('Order', () => {
    it('should create valid order object', () => {
      const order: Order = {
        clientOrderId: 'test-client-id-123',
        binanceOrderId: 123456789,
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'NEW',
        data: {
          price: '50000',
          origQty: '0.5',
          executedQty: '0',
        },
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }
      expect(order.clientOrderId).toBe('test-client-id-123')
      expect(order.binanceOrderId).toBe(123456789)
      expect(order.status).toBe('NEW')
    })

    it('should allow optional binanceOrderId', () => {
      const order: Order = {
        clientOrderId: 'test-client-id',
        marketType: 'SPOT',
        symbol: 'ETHUSDT',
        side: 'SELL',
        orderType: 'MARKET',
        status: 'FILLED',
        data: {},
        createdAt: '2026-03-01T00:00:00Z',
        updatedAt: '2026-03-01T00:00:00Z',
      }
      expect(order.binanceOrderId).toBeUndefined()
    })
  })

  // Test OrderListResponse
  describe('OrderListResponse', () => {
    it('should create valid order list response', () => {
      const response: OrderListResponse = {
        orders: [
          {
            clientOrderId: 'order-1',
            marketType: 'FUTURES',
            symbol: 'BTCUSDT',
            side: 'BUY',
            orderType: 'LIMIT',
            status: 'NEW',
            data: {},
            createdAt: '2026-03-01T00:00:00Z',
            updatedAt: '2026-03-01T00:00:00Z',
          },
        ],
        count: 1,
      }
      expect(response.orders).toHaveLength(1)
      expect(response.count).toBe(1)
    })

    it('should handle empty orders list', () => {
      const response: OrderListResponse = {
        orders: [],
        count: 0,
      }
      expect(response.orders).toHaveLength(0)
      expect(response.count).toBe(0)
    })
  })

  // Test OrderUpdate
  describe('OrderUpdate', () => {
    it('should create valid order update object', () => {
      const update: OrderUpdate = {
        clientOrderId: 'test-client-id',
        binanceOrderId: 123456789,
        marketType: 'FUTURES',
        symbol: 'BTCUSDT',
        side: 'BUY',
        orderType: 'LIMIT',
        status: 'FILLED',
        data: {
          price: '50000',
          executedQty: '0.5',
        },
        updatedAt: '2026-03-01T00:00:00Z',
      }
      expect(update.status).toBe('FILLED')
      expect(update.updatedAt).toBe('2026-03-01T00:00:00Z')
    })
  })
})
