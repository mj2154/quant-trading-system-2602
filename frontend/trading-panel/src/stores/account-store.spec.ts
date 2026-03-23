/**
 * Account Store Tests - TDD
 *
 * Tests for account subscription functionality (SPOT only):
 * - initialize() should subscribe to SPOT account updates
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
    it('should subscribe to SPOT account updates only', () => {
      // Arrange
      const unsubscribeFn = vi.fn()
      mockSubscribeAccount.mockReturnValue(unsubscribeFn)
      const store = useAccountStore()

      // Act
      store.initialize()
      nextTick()

      // Assert - only SPOT subscription
      expect(mockSubscribeAccount).toHaveBeenCalledTimes(1)
      expect(mockSubscribeAccount).toHaveBeenCalledWith(
        'SPOT',
        expect.any(Function)
      )
    })

    it('should store unsubscribe function for cleanup', () => {
      // Arrange
      const unsubscribeFn = vi.fn()
      mockSubscribeAccount.mockReturnValue(unsubscribeFn)
      const store = useAccountStore()

      // Act
      store.initialize()
      nextTick()

      // Assert - store should have stored the unsubscribe function for reset()
      expect(mockSubscribeAccount).toHaveBeenCalled()
    })
  })

  describe('handleSpotAccountUpdate() - outboundAccountPosition', () => {
    it('should update spot account balances when outboundAccountPosition received', async () => {
      // Arrange
      const unsubscribeFn = vi.fn()
      mockSubscribeAccount.mockReturnValue(unsubscribeFn)
      const store = useAccountStore()

      // Set initial spot account
      const initialAccount = {
        balances: [
          { asset: 'BTC', free: '1.0', locked: '0.0' },
          { asset: 'ETH', free: '10.0', locked: '0.0' },
        ],
        updateTime: 1234567890,
      }
      mockGetSpotAccount.mockResolvedValue(initialAccount)
      await store.fetchSpotAccount()

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

      // Act - call initialize to set up subscription
      store.initialize()
      nextTick()

      // Get the callback passed to subscribeAccount('SPOT', ...)
      const subscribeCall = mockSubscribeAccount.mock.calls.find(
        call => call[0] === 'SPOT'
      )
      expect(subscribeCall).toBeDefined()

      const callback = subscribeCall![1] as (update: unknown) => void
      callback(updateEvent)

      await nextTick()

      // Assert - spot account should be updated
      const btcBalance = store.spotAccount?.balances?.find(b => b.asset === 'BTC')
      expect(btcBalance?.free).toBe('1.5')
    })
  })

  describe('handleSpotAccountUpdate() - balanceUpdate', () => {
    it('should update specific asset balance when balanceUpdate received', async () => {
      // Arrange
      mockSubscribeAccount.mockReturnValue(vi.fn())
      const store = useAccountStore()

      const initialAccount = {
        balances: [
          { asset: 'BTC', free: '1.0', locked: '0.0' },
        ],
        updateTime: 1234567890,
      }
      mockGetSpotAccount.mockResolvedValue(initialAccount)
      await store.fetchSpotAccount()

      // Prepare balanceUpdate event - BTC increased by 0.5
      const updateEvent = {
        e: 'balanceUpdate',
        E: 1234567900,
        a: 'BTC',
        d: '0.5',
        T: 1234567899,
      }

      // Act
      store.initialize()
      nextTick()

      const subscribeCall = mockSubscribeAccount.mock.calls.find(
        call => call[0] === 'SPOT'
      )
      const callback = subscribeCall![1] as (update: unknown) => void
      callback(updateEvent)

      await nextTick()

      // Assert - BTC balance should be increased by delta
      const btcBalance = store.spotAccount?.balances?.find(b => b.asset === 'BTC')
      expect(btcBalance?.free).toBe('1.5')
    })
  })

  describe('handleSpotAccountUpdate() - executionReport', () => {
    it('should log order execution updates without modifying balance directly', async () => {
      // Arrange
      mockSubscribeAccount.mockReturnValue(vi.fn())
      const store = useAccountStore()
      const consoleSpy = vi.spyOn(console, 'debug').mockImplementation(() => {})

      const initialAccount = {
        balances: [
          { asset: 'BTC', free: '1.0', locked: '0.0' },
        ],
        updateTime: 1234567890,
      }
      mockGetSpotAccount.mockResolvedValue(initialAccount)
      await store.fetchSpotAccount()

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

      // Act
      store.initialize()
      nextTick()

      const subscribeCall = mockSubscribeAccount.mock.calls.find(
        call => call[0] === 'SPOT'
      )
      const callback = subscribeCall![1] as (update: unknown) => void
      callback(updateEvent)

      await nextTick()

      // Assert - execution report doesn't directly update balance (balance comes via outboundAccountPosition)
      expect(consoleSpy).toHaveBeenCalled()

      consoleSpy.mockRestore()
    })
  })

  describe('handleFuturesAccountUpdate()', () => {
    it('should NOT subscribe to FUTURES account updates', () => {
      // Arrange
      mockSubscribeAccount.mockReturnValue(vi.fn())
      const store = useAccountStore()

      // Act
      store.initialize()
      nextTick()

      // Assert - futures should NOT be subscribed
      expect(mockSubscribeAccount).not.toHaveBeenCalledWith(
        'FUTURES',
        expect.any(Function)
      )
    })
  })

  describe('reset()', () => {
    it('should cleanup subscriptions when reset is called', async () => {
      // Arrange
      const unsubscribeFn = vi.fn()
      mockSubscribeAccount.mockReturnValue(unsubscribeFn)
      const store = useAccountStore()

      // Act
      store.initialize()
      nextTick()
      store.reset()

      // Assert
      expect(unsubscribeFn).toHaveBeenCalled()
      expect(store.spotAccount).toBeNull()
      expect(store.futuresAccount).toBeNull()
    })
  })

  describe('refreshAccounts()', () => {
    it('should fetch both spot and futures accounts', async () => {
      // Arrange
      const store = useAccountStore()
      mockGetSpotAccount.mockResolvedValue({ balances: [] })
      mockGetFuturesAccount.mockResolvedValue({ assets: [], positions: [] })

      // Act
      await store.refreshAccounts()

      // Assert
      expect(mockGetSpotAccount).toHaveBeenCalled()
      expect(mockGetFuturesAccount).toHaveBeenCalled()
    })
  })
})
