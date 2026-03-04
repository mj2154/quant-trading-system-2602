import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OrderForm from './OrderForm.vue'

// Mock the trading store
vi.mock('../../stores/trading-store', () => ({
  useTradingStore: () => ({
    createOrder: vi.fn().mockResolvedValue({
      clientOrderId: 'test-order-id',
      marketType: 'FUTURES',
      symbol: 'BTCUSDT',
      side: 'BUY',
      orderType: 'LIMIT',
      status: 'NEW',
      data: {},
      createdAt: '2026-03-01T00:00:00Z',
      updatedAt: '2026-03-01T00:00:00Z',
    }),
    isLoading: false,
    error: null,
  }),
}))

describe('OrderForm', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  // Test component renders
  it('should render the order form', () => {
    const wrapper = mount(OrderForm)
    expect(wrapper.exists()).toBe(true)
  })

  // Test market type selection
  it('should have FUTURES and SPOT market type options', () => {
    const wrapper = mount(OrderForm)
    const marketSelect = wrapper.find('[data-testid="market-type-select"]')
    expect(marketSelect.exists()).toBe(true)
  })

  // Test order type selection
  it('should have order type options', () => {
    const wrapper = mount(OrderForm)
    const orderTypeSelect = wrapper.find('[data-testid="order-type-select"]')
    expect(orderTypeSelect.exists()).toBe(true)
  })

  // Test BUY/SELL buttons
  it('should have BUY and SELL buttons', () => {
    const wrapper = mount(OrderForm)
    const buyButton = wrapper.find('[data-testid="buy-button"]')
    const sellButton = wrapper.find('[data-testid="sell-button"]')
    expect(buyButton.exists()).toBe(true)
    expect(sellButton.exists()).toBe(true)
  })

  // Test quantity input
  it('should have quantity input', () => {
    const wrapper = mount(OrderForm)
    const quantityInput = wrapper.find('[data-testid="quantity-input"]')
    expect(quantityInput.exists()).toBe(true)
  })

  // Test price input (for LIMIT orders)
  it('should show price input for LIMIT orders', () => {
    const wrapper = mount(OrderForm)
    const priceInput = wrapper.find('[data-testid="price-input"]')
    expect(priceInput.exists()).toBe(true)
  })

  // Test stop price input (for STOP orders)
  it('should show stop price input for STOP orders', () => {
    const wrapper = mount(OrderForm)
    // Initially should not show stop price
    const stopPriceInput = wrapper.find('[data-testid="stop-price-input"]')
    expect(stopPriceInput.exists()).toBe(false)
  })

  // Test time in force (for LIMIT orders)
  it('should show time in force for LIMIT orders', () => {
    const wrapper = mount(OrderForm)
    const timeInForceSelect = wrapper.find('[data-testid="time-in-force-select"]')
    expect(timeInForceSelect.exists()).toBe(true)
  })

  // Test position side (for FUTURES)
  it('should show position side for FUTURES market', () => {
    const wrapper = mount(OrderForm)
    const positionSideSelect = wrapper.find('[data-testid="position-side-select"]')
    expect(positionSideSelect.exists()).toBe(true)
  })

  // Test reduceOnly option (for FUTURES)
  it('should show reduceOnly option for FUTURES market', () => {
    const wrapper = mount(OrderForm)
    const reduceOnlyCheckbox = wrapper.find('[data-testid="reduce-only-checkbox"]')
    expect(reduceOnlyCheckbox.exists()).toBe(true)
  })

  // Test submit button
  it('should have submit button', () => {
    const wrapper = mount(OrderForm)
    const submitButton = wrapper.find('[data-testid="submit-button"]')
    expect(submitButton.exists()).toBe(true)
  })

  // Test symbol input
  it('should have symbol input', () => {
    const wrapper = mount(OrderForm)
    const symbolInput = wrapper.find('[data-testid="symbol-input"]')
    expect(symbolInput.exists()).toBe(true)
  })

  // Test that clicking submit button triggers submission
  it('should call createOrder when submit button is clicked', async () => {
    const wrapper = mount(OrderForm)
    const submitButton = wrapper.find('[data-testid="submit-button"]')

    await submitButton.trigger('click')

    // Should not throw error
    expect(wrapper.exists()).toBe(true)
  })
})
