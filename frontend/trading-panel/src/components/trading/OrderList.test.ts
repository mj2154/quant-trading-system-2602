import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OrderList from './OrderList.vue'
import type { Order } from '../../types/trading-types'

// Mock trading store
const mockOrders: Order[] = [
  {
    clientOrderId: 'order-1',
    binanceOrderId: 123456,
    marketType: 'FUTURES',
    symbol: 'BTCUSDT',
    side: 'BUY',
    orderType: 'LIMIT',
    status: 'NEW',
    data: { price: '50000', quantity: '0.5' },
    createdAt: '2026-03-01T10:00:00Z',
    updatedAt: '2026-03-01T10:00:00Z',
  },
  {
    clientOrderId: 'order-2',
    binanceOrderId: 123457,
    marketType: 'SPOT',
    symbol: 'ETHUSDT',
    side: 'SELL',
    orderType: 'MARKET',
    status: 'FILLED',
    data: { executedQty: '1.0' },
    createdAt: '2026-03-01T09:00:00Z',
    updatedAt: '2026-03-01T09:30:00Z',
  },
]

vi.mock('../../stores/trading-store', () => ({
  useTradingStore: () => ({
    orders: mockOrders,
    openOrders: [mockOrders[0]],
    isLoading: false,
    error: null,
    fetchOrders: vi.fn().mockResolvedValue({ orders: mockOrders, count: 2 }),
    cancelOrder: vi.fn().mockResolvedValue({ ...mockOrders[0], status: 'CANCELED' }),
    setCurrentOrder: vi.fn(),
  }),
}))

vi.mock('naive-ui', async () => {
  const actual = await vi.importActual('naive-ui')
  return {
    ...actual,
    createDiscreteApi: () => ({
      message: {
        success: vi.fn(),
        error: vi.fn(),
      },
    }),
  }
})

describe('OrderList', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // Test component renders
  it('should render the order list', () => {
    const wrapper = mount(OrderList)
    expect(wrapper.exists()).toBe(true)
  })

  // Test renders properly
  it('should render without errors', () => {
    const wrapper = mount(OrderList)
    expect(wrapper.exists()).toBe(true)
  })

  // Test filter inputs exist
  it('should have market type filter', () => {
    const wrapper = mount(OrderList)
    const marketFilter = wrapper.find('[data-testid="market-filter"]')
    expect(marketFilter.exists()).toBe(true)
  })

  it('should have status filter', () => {
    const wrapper = mount(OrderList)
    const statusFilter = wrapper.find('[data-testid="status-filter"]')
    expect(statusFilter.exists()).toBe(true)
  })

  it('should have side filter', () => {
    const wrapper = mount(OrderList)
    const sideFilter = wrapper.find('[data-testid="side-filter"]')
    expect(sideFilter.exists()).toBe(true)
  })

  // Test refresh button
  it('should have refresh button', () => {
    const wrapper = mount(OrderList)
    const refreshButton = wrapper.find('[data-testid="refresh-button"]')
    expect(refreshButton.exists()).toBe(true)
  })
})
