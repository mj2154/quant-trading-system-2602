/**
 * useMarketTicker - Composable for market ticker data (price)
 * Provides real-time price fetching and subscription for spot trading
 */

import { ref, onUnmounted } from 'vue'

// Ticker data from Binance
export interface Ticker {
  symbol: string
  lastPrice: string
  priceChange: string
  priceChangePercent: string
  highPrice: string
  lowPrice: string
  volume: string
  quoteVolume: string
  openPrice: string
}

// WebSocket connection for market data
let wsConnection: WebSocket | null = null
const tickerHandlers = new Map<string, (ticker: Ticker) => void>()

function getMarketWebSocketUrl(): string {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_WS_HOST || 'localhost:8000'
  return `${wsProtocol}//${host}/ws/market`
}

function connectMarketWebSocket(): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      resolve(wsConnection)
      return
    }

    try {
      wsConnection = new WebSocket(getMarketWebSocketUrl())

      wsConnection.onopen = () => {
        console.log('[useMarketTicker] WebSocket connected')
        resolve(wsConnection!)
      }

      wsConnection.onerror = (error) => {
        console.error('[useMarketTicker] WebSocket error:', error)
        reject(error)
      }

      wsConnection.onclose = () => {
        console.log('[useMarketTicker] WebSocket closed')
        wsConnection = null
      }

      wsConnection.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          // Handle ticker update messages
          if (message.data?.symbol) {
            const ticker = message.data as Ticker
            const handler = tickerHandlers.get(ticker.symbol)
            if (handler) {
              handler(ticker)
            }
          }
        } catch (e) {
          console.error('[useMarketTicker] Failed to parse message:', e)
        }
      }
    } catch (error) {
      reject(error)
    }
  })
}

function subscribeTickerMessage(symbol: string, handler: (ticker: Ticker) => void): void {
  tickerHandlers.set(symbol, handler)

  // Send subscription message if WebSocket is connected
  if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
    wsConnection.send(JSON.stringify({
      type: 'SUBSCRIBE',
      symbols: [symbol],
    }))
  }
}

function unsubscribeTickerMessage(symbol: string): void {
  tickerHandlers.delete(symbol)

  // Send unsubscribe message if WebSocket is connected
  if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
    wsConnection.send(JSON.stringify({
      type: 'UNSUBSCRIBE',
      symbols: [symbol],
    }))
  }
}

export function useMarketTicker() {
  const currentTicker = ref<Ticker | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const unsubscribeRef = ref<(() => void) | null>(null)

  /**
   * Fetch ticker data once (for initial price display)
   * Falls back to REST API if WebSocket is not available
   */
  async function fetchTicker(symbol: string): Promise<Ticker | null> {
    isLoading.value = true
    error.value = null

    try {
      // Get API host from environment
      const apiHost = import.meta.env.VITE_API_HOST || 'http://localhost:8000'
      const response = await fetch(`${apiHost}/api/v1/market/ticker?symbol=${symbol}`)

      if (!response.ok) {
        throw new Error(`Failed to fetch ticker: ${response.statusText}`)
      }

      const data = await response.json()
      const ticker: Ticker = {
        symbol: data.symbol || symbol,
        lastPrice: data.lastPrice || data.last_price || '0',
        priceChange: data.priceChange || data.price_change || '0',
        priceChangePercent: data.priceChangePercent || data.price_change_percent || '0',
        highPrice: data.highPrice || data.high_price || '0',
        lowPrice: data.lowPrice || data.low_price || '0',
        volume: data.volume || '0',
        quoteVolume: data.quoteVolume || data.quote_volume || '0',
        openPrice: data.openPrice || data.open_price || '0',
      }

      currentTicker.value = ticker
      return ticker
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch ticker'
      console.error('[useMarketTicker] Fetch error:', e)
      return null
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Subscribe to real-time ticker updates via WebSocket
   * Returns unsubscribe function
   */
  function subscribeTicker(
    symbol: string,
    callback: (ticker: Ticker) => void
  ): () => void {
    // Clean up previous subscription
    if (unsubscribeRef.value) {
      unsubscribeRef.value()
    }

    // Store the callback
    const handler = (ticker: Ticker) => {
      currentTicker.value = ticker
      callback(ticker)
    }

    // Connect and subscribe
    connectMarketWebSocket()
      .then((ws) => {
        subscribeTickerMessage(symbol, handler)

        // Send subscription message
        ws.send(JSON.stringify({
          type: 'SUBSCRIBE',
          symbols: [symbol],
        }))
      })
      .catch((e) => {
        console.error('[useMarketTicker] Failed to subscribe:', e)
        error.value = 'Failed to connect to market feed'
      })

    // Return unsubscribe function
    const unsubscribe = () => {
      unsubscribeTickerMessage(symbol)
      unsubscribeRef.value = null
    }

    unsubscribeRef.value = unsubscribe
    return unsubscribe
  }

  /**
   * Get current price as number
   */
  function getCurrentPrice(): number {
    if (!currentTicker.value) return 0
    return parseFloat(currentTicker.value.lastPrice) || 0
  }

  /**
   * Clean up on unmount
   */
  onUnmounted(() => {
    if (unsubscribeRef.value) {
      unsubscribeRef.value()
    }
  })

  return {
    // State
    currentTicker,
    isLoading,
    error,

    // Actions
    fetchTicker,
    subscribeTicker,
    getCurrentPrice,
  }
}
