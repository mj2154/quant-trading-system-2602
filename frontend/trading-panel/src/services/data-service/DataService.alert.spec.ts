/**
 * DataService Alert Methods Tests - TDD
 *
 * Tests for alert CRUD operations in DataService:
 * - createAlert()
 * - getAlert()
 * - updateAlert()
 * - deleteAlert()
 * - enableAlert()
 * - disableAlert()
 * - subscribeAllSignals()
 *
 * Following TDD workflow: RED -> GREEN -> REFACTOR
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock WSClient
const mockWSClient = {
  connect: vi.fn().mockResolvedValue(undefined),
  disconnect: vi.fn(),
  isConnected: true,
  request: vi.fn(),
  subscribe: vi.fn(() => () => {}),
  unsubscribe: vi.fn(),
  getSubscriptions: vi.fn().mockReturnValue([]),
}

// Mock the WSClient module
vi.mock('../../libs/ws-client/WSClient', () => ({
  WSClient: vi.fn(function () {
    return mockWSClient
  }),
}))

// Mock environment variables
vi.stubGlobal('import.meta', {
  env: {
    VITE_WS_HOST: 'localhost:8000',
  },
})

// Import after mocking
import { DataService } from './DataService'

describe('DataService Alert Methods', () => {
  let dataService: DataService

  beforeEach(() => {
    vi.clearAllMocks()
    // Reset singleton
    ;(DataService as unknown as { instance: DataService | null }).instance = null
    dataService = DataService.getInstance()
  })

  afterEach(() => {
    vi.resetModules()
  })

  describe('createAlert()', () => {
    it('should call CREATE_ALERT_CONFIG with correct params', async () => {
      // Arrange
      const alertConfig = {
        name: 'Test Alert',
        description: 'Test Description',
        strategyType: 'MACDResonanceStrategyV5',
        symbol: 'BINANCE:BTCUSDT',
        interval: '60',
        triggerType: 'each_kline_close',
        params: { fast1: 12, slow1: 26, signal1: 9, fast2: 5, slow2: 10, signal2: 4 },
        isEnabled: true,
      }

      const mockResponse = {
        configs: [{
          id: 'test-id-123',
          name: alertConfig.name,
          description: alertConfig.description,
          strategyType: alertConfig.strategyType,
          symbol: alertConfig.symbol,
          interval: alertConfig.interval,
          triggerType: alertConfig.triggerType,
          params: { macd1_fastperiod: 12, macd1_slowperiod: 26, macd1_signalperiod: 9, macd2_fastperiod: 5, macd2_slowperiod: 10, macd2_signalperiod: 4 },
          isEnabled: alertConfig.isEnabled,
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        }],
      }

      mockWSClient.request.mockResolvedValue(mockResponse)

      // Act
      const result = await dataService.createAlert(alertConfig)

      // Assert
      expect(mockWSClient.request).toHaveBeenCalledWith('CREATE_ALERT_CONFIG', expect.objectContaining({
        name: alertConfig.name,
        description: alertConfig.description,
        strategyType: alertConfig.strategyType,
        symbol: alertConfig.symbol,
        interval: alertConfig.interval,
        triggerType: alertConfig.triggerType,
        isEnabled: alertConfig.isEnabled,
      }))

      expect(result).toBeDefined()
      expect(result.id).toBe('test-id-123')
    })

    it('should handle empty params', async () => {
      // Arrange
      const alertConfig = {
        name: 'Minimal Alert',
        strategyType: 'MACDResonanceStrategyV5',
        symbol: 'BINANCE:ETHUSDT',
        interval: '60',
      }

      const mockResponse = {
        configs: [{
          id: 'test-id-456',
          name: alertConfig.name,
          description: null,
          strategyType: alertConfig.strategyType,
          symbol: alertConfig.symbol,
          interval: alertConfig.interval,
          triggerType: 'each_kline_close',
          params: null,
          isEnabled: true,
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        }],
      }

      mockWSClient.request.mockResolvedValue(mockResponse)

      // Act
      const result = await dataService.createAlert(alertConfig)

      // Assert
      expect(result).toBeDefined()
      expect(result?.id).toBe('test-id-456')
    })

    it('should throw error when not connected', async () => {
      // Arrange - create a new instance with disconnected state
      ;(DataService as unknown as { instance: DataService | null }).instance = null
      const disconnectedDataService = DataService.getInstance()
      // Override isConnected to return false
      Object.defineProperty(disconnectedDataService, 'isConnected', {
        get: () => false,
        configurable: true,
      })

      // Act & Assert
      await expect(disconnectedDataService.createAlert({
        name: 'Test',
        strategyType: 'macd',
        symbol: 'BTCUSDT',
        interval: '60',
      })).rejects.toThrow()
    })
  })

  describe('getAlert()', () => {
    it('should call GET_ALERT_CONFIG with correct id', async () => {
      // Arrange
      const alertId = 'alert-123'
      const mockResponse = {
        configs: [{
          id: alertId,
          name: 'Test Alert',
          strategyType: 'MACDResonanceStrategyV5',
          symbol: 'BINANCE:BTCUSDT',
          interval: '60',
          isEnabled: true,
          params: null,
        }],
      }

      mockWSClient.request.mockResolvedValue(mockResponse)

      // Act
      const result = await dataService.getAlert(alertId)

      // Assert
      expect(mockWSClient.request).toHaveBeenCalledWith('GET_ALERT_CONFIG', { id: alertId })
      expect(result).toBeDefined()
      expect(result?.id).toBe(alertId)
    })

    it('should return null for non-existent alert', async () => {
      // Arrange
      mockWSClient.request.mockResolvedValue({ configs: [] })

      // Act
      const result = await dataService.getAlert('non-existent')

      // Assert
      expect(result).toBeNull()
    })
  })

  describe('updateAlert()', () => {
    it('should call UPDATE_ALERT_CONFIG with correct params', async () => {
      // Arrange
      const alertId = 'alert-123'
      const updates = {
        name: 'Updated Alert',
        isEnabled: false,
      }

      const mockResponse = {
        configs: [{
          id: alertId,
          name: 'Updated Alert',
          strategyType: 'MACDResonanceStrategyV5',
          symbol: 'BINANCE:BTCUSDT',
          interval: '60',
          isEnabled: false,
          params: null,
        }],
      }

      mockWSClient.request.mockResolvedValue(mockResponse)

      // Act
      const result = await dataService.updateAlert(alertId, updates)

      // Assert
      expect(mockWSClient.request).toHaveBeenCalledWith('UPDATE_ALERT_CONFIG', expect.objectContaining({
        id: alertId,
        name: updates.name,
        isEnabled: updates.isEnabled,
      }))

      expect(result).toBeDefined()
      expect(result?.name).toBe('Updated Alert')
    })

    it('should handle partial updates', async () => {
      // Arrange
      const alertId = 'alert-456'
      const updates = { name: 'New Name' }

      const mockResponse = {
        configs: [{
          id: alertId,
          name: 'New Name',
          strategyType: 'MACDResonanceStrategyV5',
          symbol: 'BINANCE:BTCUSDT',
          interval: '60',
          isEnabled: true,
          params: null,
        }],
      }

      mockWSClient.request.mockResolvedValue(mockResponse)

      // Act
      const result = await dataService.updateAlert(alertId, updates)

      // Assert
      expect(result?.name).toBe('New Name')
    })
  })

  describe('deleteAlert()', () => {
    it('should call DELETE_ALERT_CONFIG with correct id', async () => {
      // Arrange
      const alertId = 'alert-123'
      mockWSClient.request.mockResolvedValue({ success: true })

      // Act
      const result = await dataService.deleteAlert(alertId)

      // Assert
      expect(mockWSClient.request).toHaveBeenCalledWith('DELETE_ALERT_CONFIG', { id: alertId })
      expect(result).toBe(true)
    })

    it('should handle delete failure', async () => {
      // Arrange
      const alertId = 'alert-123'
      mockWSClient.request.mockRejectedValue(new Error('Delete failed'))

      // Act & Assert
      await expect(dataService.deleteAlert(alertId)).rejects.toThrow('Delete failed')
    })
  })

  describe('enableAlert()', () => {
    it('should call ENABLE_ALERT_CONFIG with correct id', async () => {
      // Arrange
      const alertId = 'alert-123'
      const mockResponse = { id: alertId, isEnabled: true }

      mockWSClient.request.mockResolvedValue(mockResponse)

      // Act
      const result = await dataService.enableAlert(alertId)

      // Assert
      expect(mockWSClient.request).toHaveBeenCalledWith('ENABLE_ALERT_CONFIG', { id: alertId })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('disableAlert()', () => {
    it('should call DISABLE_ALERT_CONFIG with correct id', async () => {
      // Arrange
      const alertId = 'alert-123'
      const mockResponse = { id: alertId, isEnabled: false }

      mockWSClient.request.mockResolvedValue(mockResponse)

      // Act
      const result = await dataService.disableAlert(alertId)

      // Assert
      expect(mockWSClient.request).toHaveBeenCalledWith('DISABLE_ALERT_CONFIG', { id: alertId })
      expect(result).toEqual(mockResponse)
    })
  })

  describe('subscribeAllSignals()', () => {
    it('should subscribe to multiple alert signals', async () => {
      // Arrange
      const alertIds = ['alert-1', 'alert-2', 'alert-3']
      const callback = vi.fn()

      mockWSClient.subscribe.mockImplementation(() => () => {})

      // Act
      const unsubscribe = dataService.subscribeAllSignals(alertIds, callback)

      // Assert
      expect(mockWSClient.subscribe).toHaveBeenCalledTimes(alertIds.length)

      // Verify each alert ID was subscribed
      alertIds.forEach((alertId) => {
        expect(mockWSClient.subscribe).toHaveBeenCalledWith(
          `SIGNAL:${alertId}`,
          expect.any(Function)
        )
      })

      // Cleanup
      unsubscribe()
    })

    it('should return unsubscribe function for all subscriptions', () => {
      // Arrange
      const alertIds = ['alert-1', 'alert-2']
      const callback = vi.fn()

      const unsubscribers = [vi.fn(), vi.fn()]
      let callIndex = 0
      mockWSClient.subscribe.mockImplementation(() => unsubscribers[callIndex++])

      // Act
      const unsubscribe = dataService.subscribeAllSignals(alertIds, callback)
      unsubscribe()

      // Assert
      expect(unsubscribers[0]).toHaveBeenCalled()
      expect(unsubscribers[1]).toHaveBeenCalled()
    })

    it('should handle empty alertIds array', () => {
      // Arrange
      const callback = vi.fn()

      // Act
      const unsubscribe = dataService.subscribeAllSignals([], callback)

      // Assert
      expect(mockWSClient.subscribe).not.toHaveBeenCalled()
      expect(unsubscribe).toBeDefined()
      expect(typeof unsubscribe).toBe('function')
    })
  })

  describe('Parameter Conversion', () => {
    it('should convert frontend params to backend format when creating alert', async () => {
      // Arrange - frontend uses short param names
      const alertConfig = {
        name: 'Test Alert',
        strategyType: 'MACDResonanceStrategyV5',
        symbol: 'BINANCE:BTCUSDT',
        interval: '60',
        params: {
          fast1: 12,
          slow1: 26,
          signal1: 9,
          fast2: 5,
          slow2: 10,
          signal2: 4,
        },
      }

      const mockResponse = {
        id: 'test-id',
        ...alertConfig,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      }

      mockWSClient.request.mockResolvedValue(mockResponse)

      // Act
      await dataService.createAlert(alertConfig)

      // Assert - should convert to backend format
      const requestCall = mockWSClient.request.mock.calls[0]
      const requestParams = requestCall[1] as Record<string, unknown>

      expect(requestParams.params).toEqual({
        macd1_fastperiod: 12,
        macd1_slowperiod: 26,
        macd1_signalperiod: 9,
        macd2_fastperiod: 5,
        macd2_slowperiod: 10,
        macd2_signalperiod: 4,
      })
    })

    it('should convert backend params to frontend format when getting alert', async () => {
      // Arrange - backend returns full param names
      const alertId = 'alert-123'
      const mockResponse = {
        id: alertId,
        name: 'Test Alert',
        strategyType: 'MACDResonanceStrategyV5',
        symbol: 'BINANCE:BTCUSDT',
        interval: '60',
        params: {
          macd1_fastperiod: 12,
          macd1_slowperiod: 26,
          macd1_signalperiod: 9,
          macd2_fastperiod: 5,
          macd2_slowperiod: 10,
          macd2_signalperiod: 4,
        },
        isEnabled: true,
      }

      mockWSClient.request.mockResolvedValue(mockResponse)

      // Act
      const result = await dataService.getAlert(alertId)

      // Assert - should convert to frontend format
      expect(result?.params).toEqual({
        fast1: 12,
        slow1: 26,
        signal1: 9,
        fast2: 5,
        slow2: 10,
        signal2: 4,
      })
    })
  })
})
