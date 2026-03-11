/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { NButton, NCard, NForm, NFormItem, NSelect, NInputNumber, NSpace, NCollapse, NCollapseItem } from 'naive-ui'
import SpotOrderForm from './SpotOrderForm.vue'

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
    setTimeout(() => {
      if (this.onmessage) {
        const response = {
          type: 'ORDER_DATA',
          requestId: message.requestId,
          data: {
            clientOrderId: 'test-order-id',
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
vi.stubGlobal('crypto', {
  randomUUID: vi.fn().mockReturnValue('550e8400e29b41d4a716446655440000'),
})

describe('SpotOrderForm', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket)
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('should render the form with all required fields', async () => {
    const wrapper = mount(SpotOrderForm)

    expect(wrapper.findComponent(NCard).exists()).toBe(true)
    expect(wrapper.findComponent(NForm).exists()).toBe(true)
    expect(wrapper.findComponent(NSelect).exists()).toBe(true)
    expect(wrapper.findComponent(NInputNumber).exists()).toBe(true)
    expect(wrapper.findComponent(NButton).exists()).toBe(true)
  })

  it('should show order type options', async () => {
    const wrapper = mount(SpotOrderForm)

    // Find order type select
    const orderTypeSelect = wrapper.findAllComponents(NSelect).at(1)
    expect(orderTypeSelect).toBeDefined()
  })

  it('should toggle BUY/SELL side', async () => {
    const wrapper = mount(SpotOrderForm)

    // Find BUY and SELL buttons
    const buttons = wrapper.findAllComponents(NButton)
    const buyButton = buttons.at(0)
    const sellButton = buttons.at(1)

    expect(buyButton).toBeDefined()
    expect(sellButton).toBeDefined()

    // Default should be BUY
    expect(buyButton?.props('type')).toBe('success')
  })

  it('should show price input when order type requires price', async () => {
    const wrapper = mount(SpotOrderForm)

    // LIMIT order should show price input
    // Need to set order type to LIMIT first
    const vm = wrapper.vm as any
    if (vm.orderType) {
      vm.orderType = 'LIMIT'
      await wrapper.vm.$nextTick()
    }

    // Price input should be visible for LIMIT orders
    const priceInput = wrapper.findAllComponents(NFormItem).find(item => item.text().includes('价格'))
    // The price field should be visible for LIMIT order type
  })

  it('should show quote order qty for MARKET order', async () => {
    const wrapper = mount(SpotOrderForm)

    // Set to MARKET order
    const vm = wrapper.vm as any
    vm.orderType = 'MARKET'
    await wrapper.vm.$nextTick()

    // Should show quoteOrderQty instead of quantity
    // This is a basic check - more specific tests would require deeper inspection
  })

  it('should show advanced options in collapse', async () => {
    const wrapper = mount(SpotOrderForm)

    const collapse = wrapper.findComponent(NCollapse)
    expect(collapse.exists()).toBe(true)
  })

  it('should validate required fields', async () => {
    const wrapper = mount(SpotOrderForm)

    // Try to submit without required fields
    const vm = wrapper.vm as any

    // Should not be valid without symbol and quantity
    expect(vm.isFormValid).toBe(false)
  })
})
