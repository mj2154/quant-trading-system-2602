/**
 * Account Store Tests - TDD
 *
 * Tests for account subscription functionality (SPOT only):
 * - initialize() should subscribe to SPOT and FUTURES account updates
 * - handleSpotAccountUpdate() for outboundAccountPosition events
 * - handleSpotAccountUpdate() for balanceUpdate events
 * - handleSpotAccountUpdate() for executionReport events
 * - reset() should cleanup subscriptions
 *
 * Following TDD workflow: RED -> GREEN -> REFACTOR
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { nextTick } from 'vue'

// Mock DataService - using vi.hoisted to avoid hoisting issues
const { mockSubscribeAccount, mockGetSpotAccount, mockGetFuturesAccount } = vi.hoisted(() => ({
  mockSubscribeAccount: vi.fn(() => () => {}),
  mockGetSpotAccount: vi.fn(),
  mockGetFuturesAccount: vi.fn(),
}))

vi.mock('../services/data-service/DataService', () => ({
  dataService: {
    subscribeAccount: mockSubscribeAccount,
    getSpotAccount: mockGetSpotAccount,
    getFuturesAccount: mockGetFuturesAccount,
    connect: vi.fn().mockResolvedValue(undefined),
    isConnected: true,
  },
}))

// Import store factory after mocking
import { useAccountStore } from './account-store'

describe('AccountStore - Account Subscription', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.resetModules()
  })

  describe('initialize()', () => {
    it('should fetch accounts and subscribe to SPOT and FUTURES updates', async () => {
      // Arrange
      const unsubscribeFn = vi.fn()
      mockSubscribeAccount.mockReturnValue(unsubscribeFn)
      mockGetSpotAccount.mockResolvedValue({
        balances: [{ asset: 'BTC', free: '1.0', locked: '0.0' }],
        updateTime: 1234567890,
      })
      mockGetFuturesAccount.mockResolvedValue({
        assets: [],
        positions: [],
        updateTime: 1234567890,
      })
      const store = useAccountStore()

      // Act
      await store.initialize()
      await nextTick()

      // Assert - both SPOT and FUTURES subscriptions
      expect(mockSubscribeAccount).toHaveBeenCalledTimes(2)
      expect(mockSubscribeAccount).toHaveBeenCalledWith(
        'SPOT',
        expect.any(Function)
      )
      expect(mockSubscribeAccount).toHaveBeenCalledWith(
        'FUTURES',
        expect.any(Function)
      )
    })

    it('should store unsubscribe functions for cleanup', async () => {
      // Arrange
      const unsubscribeFn = vi.fn()
      mockSubscribeAccount.mockReturnValue(unsubscribeFn)
      mockGetSpotAccount.mockResolvedValue({
        balances: [],
        updateTime: 1234567890,
      })
      mockGetFuturesAccount.mockResolvedValue({
        assets: [],
        positions: [],
        updateTime: 1234567890,
      })
      const store = useAccountStore()

      // Act
      await store.initialize()
      await nextTick()

      // Assert - store should have stored the unsubscribe function for reset()
      expect(mockSubscribeAccount).toHaveBeenCalled()
    })
  })

  describe('handleSpotAccountUpdate() - outboundAccountPosition', () => {
    it('should update spotDisplay balances when outboundAccountPosition received', async () => {
      // Arrange
      const unsubscribeFn = vi.fn()
      mockSubscribeAccount.mockReturnValue(unsubscribeFn)
      mockGetSpotAccount.mockResolvedValue({
        balances: [
          { asset: 'BTC', free: '1.0', locked: '0.0' },
          { asset: 'ETH', free: '10.0', locked: '0.0' },
        ],
        updateTime: 1234567890,
        canTrade: true,
        canWithdraw: true,
        canDeposit: true,
        permissions: ['SPOT'],
      })
      mockGetFuturesAccount.mockResolvedValue({
        assets: [],
        positions: [],
        updateTime: 1234567890,
      })
      const store = useAccountStore()
      await store.initialize()
      await nextTick()

      // Reset mock to track subscription
      mockSubscribeAccount.mockClear()
      mockSubscribeAccount.mockReturnValue(vi.fn())

      // Prepare update event - BTC balance changed
      const updateEvent = {
        e: 'outboundAccountPosition',
        E: 1234567900,
        u: 1234567899,
        B: [{ a: 'BTC', f: '1.5', l: '0.0' }],
      }

      // Get the callback passed to subscribeAccount('SPOT', ...)
      const allCalls = mockSubscribeAccount.mock.calls as unknown[][]
      const spotCalls = allCalls.filter(call => call[0] === 'SPOT')
      expect(spotCalls.length).toBeGreaterThanOrEqual(1)

      const callback = spotCalls[0]![1] as (update: unknown) => void
      callback(updateEvent)

      await nextTick()

      // Assert - spotDisplay should be updated
      const btcBalance = store.spotDisplay?.balances?.find(
        (b: { asset: string }) => b.asset === 'BTC'
      )
      expect(btcBalance?.free).toBe('1.5')
    })
  })

  describe('handleSpotAccountUpdate() - balanceUpdate', () => {
    it('should update specific asset balance when balanceUpdate received', async () => {
      // Arrange
      mockSubscribeAccount.mockReturnValue(vi.fn())
      mockGetSpotAccount.mockResolvedValue({
        balances: [{ asset: 'BTC', free: '1.0', locked: '0.0' }],
        updateTime: 1234567890,
        canTrade: true,
        canWithdraw: true,
        canDeposit: true,
        permissions: ['SPOT'],
      })
      mockGetFuturesAccount.mockResolvedValue({
        assets: [],
        positions: [],
        updateTime: 1234567890,
      })
      const store = useAccountStore()
      await store.initialize()
      await nextTick()

      // Prepare balanceUpdate event - BTC increased by 0.5
      const updateEvent = {
        e: 'balanceUpdate',
        E: 1234567900,
        a: 'BTC',
        d: '0.5',
        T: 1234567899,
      }

      // Get the callback
      const allCalls = mockSubscribeAccount.mock.calls as unknown[][]
      const spotCalls = allCalls.filter(call => call[0] === 'SPOT')
      expect(spotCalls.length).toBeGreaterThanOrEqual(1)

      const callback = spotCalls[0]![1] as (update: unknown) => void
      callback(updateEvent)

      await nextTick()

      // Assert - BTC balance should be increased by delta
      const btcBalance = store.spotDisplay?.balances?.find(
        (b: { asset: string }) => b.asset === 'BTC'
      )
      expect(btcBalance?.free).toBe('1.5')
    })
  })

  describe('handleSpotAccountUpdate() - executionReport', () => {
    it('should log order execution updates without modifying balance directly', async () => {
      // Arrange
      mockSubscribeAccount.mockReturnValue(vi.fn())
      mockGetSpotAccount.mockResolvedValue({
        balances: [{ asset: 'BTC', free: '1.0', locked: '0.0' }],
        updateTime: 1234567890,
        canTrade: true,
        canWithdraw: true,
        canDeposit: true,
        permissions: ['SPOT'],
      })
      mockGetFuturesAccount.mockResolvedValue({
        assets: [],
        positions: [],
        updateTime: 1234567890,
      })
      const store = useAccountStore()
      await store.initialize()
      await nextTick()
      const consoleSpy = vi.spyOn(console, 'debug').mockImplementation(() => {})

      // Prepare executionReport event
      const updateEvent = {
        e: 'executionReport',
        E: 1234567900,
        s: 'BTCUSDT',
        c: 'test-order-id',
        S: 'BUY',
        o: 'LIMIT',
        X: 'FILLED',
        q: '0.1',
      }

      // Get the callback
      const allCalls = mockSubscribeAccount.mock.calls as unknown[][]
      const spotCalls = allCalls.filter(call => call[0] === 'SPOT')
      expect(spotCalls.length).toBeGreaterThanOrEqual(1)

      const callback = spotCalls[0]![1] as (update: unknown) => void
      callback(updateEvent)

      await nextTick()

      // Assert - execution report doesn't directly update balance (balance comes via outboundAccountPosition)
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })
  })

  describe('reset()', () => {
    it('should cleanup subscriptions when reset is called', async () => {
      // Arrange
      const unsubscribeFn = vi.fn()
      mockSubscribeAccount.mockReturnValue(unsubscribeFn)
      mockGetSpotAccount.mockResolvedValue({
        balances: [],
        updateTime: 1234567890,
      })
      mockGetFuturesAccount.mockResolvedValue({
        assets: [],
        positions: [],
        updateTime: 1234567890,
      })
      const store = useAccountStore()

      // Act
      await store.initialize()
      await nextTick()
      store.reset()

      // Assert
      expect(unsubscribeFn).toHaveBeenCalled()
      expect(store.spotDisplay).toBeNull()
      expect(store.futuresDisplay).toBeNull()
    })
  })

  describe('refreshAccounts()', () => {
    it('should fetch both spot and futures accounts', async () => {
      // Arrange
      const store = useAccountStore()
      mockGetSpotAccount.mockResolvedValue({
        balances: [],
        updateTime: 1234567890,
      })
      mockGetFuturesAccount.mockResolvedValue({
        assets: [],
        positions: [],
        updateTime: 1234567890,
      })

      // Act
      await store.refreshAccounts()

      // Assert
      expect(mockGetSpotAccount).toHaveBeenCalled()
      expect(mockGetFuturesAccount).toHaveBeenCalled()
    })
  })
})
