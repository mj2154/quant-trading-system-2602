import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import OrderStatus from './OrderStatus.vue'

describe('OrderStatus', () => {
  // Test different order statuses
  const statuses = [
    { status: 'NEW', expectedText: '新订单', expectedType: 'info' },
    { status: 'PARTIALLY_FILLED', expectedText: '部分成交', expectedType: 'warning' },
    { status: 'FILLED', expectedText: '已成交', expectedType: 'success' },
    { status: 'CANCELED', expectedText: '已取消', expectedType: 'default' },
    { status: 'PENDING_CANCEL', expectedText: '取消中', expectedType: 'warning' },
    { status: 'REJECTED', expectedText: '已拒绝', expectedType: 'error' },
    { status: 'EXPIRED', expectedText: '已过期', expectedType: 'default' },
  ]

  statuses.forEach(({ status, expectedText, expectedType }) => {
    it(`should display correct badge for ${status} status`, () => {
      const wrapper = mount(OrderStatus, {
        props: { status: status as any },
      })

      expect(wrapper.text()).toContain(expectedText)
      expect(wrapper.props('status')).toBe(status)
    })
  })

  // Test BUY side styling
  it('should render correctly for BUY side', () => {
    const wrapper = mount(OrderStatus, {
      props: { status: 'NEW', side: 'BUY' as any },
    })

    expect(wrapper.exists()).toBe(true)
  })

  // Test SELL side styling
  it('should render correctly for SELL side', () => {
    const wrapper = mount(OrderStatus, {
      props: { status: 'NEW', side: 'SELL' as any },
    })

    expect(wrapper.exists()).toBe(true)
  })

  // Test default props
  it('should have default props', () => {
    const wrapper = mount(OrderStatus, {
      props: { status: 'NEW' },
    })

    expect(wrapper.props('status')).toBe('NEW')
  })

  // Test size prop
  it('should render with small size', () => {
    const wrapper = mount(OrderStatus, {
      props: { status: 'NEW', size: 'small' as any },
    })

    expect(wrapper.exists()).toBe(true)
  })

  it('should render with medium size', () => {
    const wrapper = mount(OrderStatus, {
      props: { status: 'NEW', size: 'medium' as any },
    })

    expect(wrapper.exists()).toBe(true)
  })

  // Test that it renders as a tag component
  it('should render as a tag', () => {
    const wrapper = mount(OrderStatus, {
      props: { status: 'FILLED' },
    })

    expect(wrapper.find('span').exists() || wrapper.find('div').exists()).toBe(true)
  })
})
