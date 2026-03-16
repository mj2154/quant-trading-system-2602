/**
 * 统一WebSocket客户端 - 核心类
 *
 * 严格遵循 WS协议 v2.0 设计文档
 * 文档: docs/backend/design/07-websocket-protocol.md
 *
 * 设计原则:
 * - 单一WebSocket连接
 * - 请求-响应模式 (带ACK确认)
 * - 订阅-推送模式
 * - 自动重连
 */

import {
  PROTOCOL_VERSION,
  DEFAULT_WS_CLIENT_OPTIONS,
  type WSClientOptions,
  type WSMessage,
  type WSRequestMessage,
  type ClientRequestType,
  type PendingRequest,
  type Subscription,
} from './types'

/**
 * 生成UUID v4 hex格式的requestId
 * 格式: 32字符无短横线 (如 550e8400e29b41d4a716446655440000)
 */
function generateRequestId(): string {
  return crypto.randomUUID().replace(/-/g, '')
}

/**
 * 统一WebSocket客户端
 *
 * 提供:
 * - 单一连接管理
 * - 请求-响应模式
 * - 订阅-推送模式
 * - 自动重连
 */
export class WSClient {
  private ws: WebSocket | null = null
  private options: Required<WSClientOptions>
  private connected = false
  private connecting = false

  // 待处理的请求 (requestId -> pending request)
  private pendingRequests = new Map<string, PendingRequest>()

  // 订阅者 (subscriptionKey -> subscription)
  private subscriptions = new Map<string, Subscription>()

  // 重连定时器
  private reconnectTimeoutId: number | null = null

  constructor(options: WSClientOptions) {
    this.options = {
      ...DEFAULT_WS_CLIENT_OPTIONS,
      ...options,
    }
  }

  // ==================== 连接管理 ====================

  /**
   * 获取连接状态
   */
  get isConnected(): boolean {
    return this.connected
  }

  /**
   * 连接到WebSocket服务器
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      // 如果已连接，直接resolve
      if (this.connected) {
        resolve()
        return
      }

      // 如果正在连接，等待连接完成
      if (this.connecting) {
        // 轮询等待连接完成
        const checkConnection = () => {
          if (this.connected) {
            resolve()
          } else if (!this.connecting) {
            reject(new Error('Connection failed'))
          } else {
            setTimeout(checkConnection, 50)
          }
        }
        checkConnection()
        return
      }

      this.connecting = true

      try {
        this.ws = new WebSocket(this.options.url)

        this.ws.onopen = () => {
          this.connected = true
          this.connecting = false
          this.options.onConnect()
          resolve()
        }

        this.ws.onclose = () => {
          this.handleDisconnect()
        }

        this.ws.onerror = (error) => {
          this.options.onError(new Error('WebSocket error'))
          if (!this.connected) {
            this.connecting = false
            reject(new Error('WebSocket connection failed'))
          }
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data)
        }
      } catch (error) {
        this.connecting = false
        reject(error)
      }
    })
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    this.stopReconnect()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    // 清除所有待处理的请求
    for (const [, pending] of this.pendingRequests) {
      clearTimeout(pending.timeoutId)
      pending.reject(new Error('Connection closed'))
    }
    this.pendingRequests.clear()

    // 清除所有订阅
    this.subscriptions.clear()

    this.connected = false
    this.connecting = false

    this.options.onDisconnect()
  }

  /**
   * 处理连接断开
   */
  private handleDisconnect(): void {
    const wasConnected = this.connected

    this.connected = false
    this.ws = null

    // 清除所有待处理的请求
    for (const [, pending] of this.pendingRequests) {
      clearTimeout(pending.timeoutId)
      pending.reject(new Error('Connection closed'))
    }
    this.pendingRequests.clear()

    if (wasConnected) {
      this.options.onDisconnect()
    }

    // 自动重连
    if (this.options.autoReconnect) {
      this.scheduleReconnect()
    }
  }

  /**
   * 调度重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimeoutId !== null) {
      return
    }

    this.reconnectTimeoutId = window.setTimeout(() => {
      this.reconnectTimeoutId = null

      if (this.options.autoReconnect && !this.connected) {
        this.connect().catch(() => {
          // 连接失败时会自动调度重连
        })
      }
    }, this.options.reconnectInterval)
  }

  /**
   * 停止重连
   */
  private stopReconnect(): void {
    if (this.reconnectTimeoutId !== null) {
      clearTimeout(this.reconnectTimeoutId)
      this.reconnectTimeoutId = null
    }
  }

  // ==================== 消息处理 ====================

  /**
   * 处理接收到的消息
   */
  private handleMessage(data: string): void {
    try {
      const message: WSMessage = JSON.parse(data)

      // 触发消息回调
      this.options.onMessage(message)

      // 根据消息类型分发处理
      const messageType = message.type

      // 1. 处理ACK确认
      if (messageType === 'ACK') {
        // ACK只是确认请求已收到，不需要特殊处理
        return
      }

      // 2. 处理错误响应
      if (messageType === 'ERROR') {
        const requestId = message.requestId
        if (!requestId) return
        const pending = this.pendingRequests.get(requestId)

        if (pending) {
          clearTimeout(pending.timeoutId)
          this.pendingRequests.delete(requestId)

          const errorData = message.data as { errorCode?: string; errorMessage?: string } | undefined
          const error = new Error(
            `${errorData?.errorCode || 'ERROR'}: ${errorData?.errorMessage || 'Unknown error'}`
          )
          pending.reject(error)
        }
        return
      }

      // 3. 处理推送消息 (UPDATE)
      if (messageType === 'UPDATE') {
        this.handlePushMessage(message)
        return
      }

      // 4. 处理订单更新推送
      if (messageType === 'ORDER_UPDATE') {
        this.handlePushMessage(message)
        return
      }

      // 5. 处理成功响应 (带requestId)
      const requestId = message.requestId
      if (requestId) {
        const pending = this.pendingRequests.get(requestId)

        if (pending) {
          clearTimeout(pending.timeoutId)
          this.pendingRequests.delete(requestId)
          pending.resolve(message.data)
        }
      }
    } catch (error) {
      console.error('[WSClient] Failed to parse message:', error)
    }
  }

  /**
   * 处理推送消息
   *
   * 根据 WS协议 v2.0 设计文档 (07-websocket-protocol.md)：
   * - subscriptionKey 在消息顶层，不在 data 内部
   * - content 是实际数据载荷
   *
   * 消息格式:
   * {
   *     "type": "UPDATE",
   *     "timestamp": 1703123456790,
   *     "subscriptionKey": "BINANCE:BTCUSDT@KLINE_1",
   *     "content": { ... }
   * }
   */
  private handlePushMessage(message: WSMessage): void {
    // 从消息顶层获取 subscriptionKey（不是从 data 内部）
    const subscriptionKey = (message as unknown as { subscriptionKey?: string }).subscriptionKey

    if (!subscriptionKey) {
      console.warn('[WSClient] UPDATE message missing subscriptionKey:', message)
      return
    }

    // 从消息顶层获取 content
    const content = (message as unknown as { content?: unknown }).content

    const subscription = this.subscriptions.get(subscriptionKey)

    if (subscription) {
      subscription.handler(content, subscriptionKey)
    } else {
      console.debug('[WSClient] No subscription found for key:', subscriptionKey)
    }
  }

  // ==================== 请求-响应 ====================

  /**
   * 发送请求并等待响应
   *
   * @param type 请求类型 (如 GET_SPOT_ACCOUNT)
   * @param data 请求数据
   * @returns 响应数据
   */
  async request<T>(type: ClientRequestType, data?: Record<string, unknown>): Promise<T> {
    // 确保已连接
    if (!this.connected || !this.ws) {
      await this.connect()
    }

    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        reject(new Error('WebSocket not connected'))
        return
      }

      const requestId = generateRequestId()

      // 设置超时
      const timeoutId = window.setTimeout(() => {
        this.pendingRequests.delete(requestId)
        reject(new Error(`Request ${type} timed out`))
      }, this.options.requestTimeout)

      // 存储pending request
      this.pendingRequests.set(requestId, {
        resolve: resolve as (value: unknown) => void,
        reject,
        timeoutId,
      })

      // 构建请求消息
      const request: WSRequestMessage = {
        protocolVersion: PROTOCOL_VERSION,
        type,
        requestId,
        timestamp: Date.now(),
        data,
      }

      // 发送消息
      this.ws.send(JSON.stringify(request))
    })
  }

  // ==================== 订阅管理 ====================

  /**
   * 订阅实时数据
   *
   * @param subscriptionKey 订阅键或订阅键数组 (如 'SIGNAL:alert_id' 或 ['key1', 'key2'])
   * @param handler 数据回调或 key -> handler 映射
   * @returns 取消订阅函数
   */
  subscribe(
    subscriptionKey: string | string[],
    handler: ((data: unknown, subscriptionKey?: string) => void) | Map<string, (data: unknown) => void>
  ): () => void {
    // 处理数组参数 - 批量订阅
    if (Array.isArray(subscriptionKey)) {
      return this.subscribeBatch(subscriptionKey, handler as Map<string, (data: unknown) => void>)
    }

    // 单个订阅键处理
    const key = subscriptionKey
    const singleHandler = handler as (data: unknown, subscriptionKey?: string) => void

    // 如果已经订阅，先取消
    if (this.subscriptions.has(key)) {
      this.unsubscribe(key)
    }

    // 存储订阅者
    this.subscriptions.set(key, { key, handler: singleHandler })

    // 发送订阅请求
    if (this.connected && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendSubscribeMessage('SUBSCRIBE', [key])
    }

    // 返回取消订阅函数
    return () => {
      this.unsubscribe(key)
    }
  }

  /**
   * 批量订阅实时数据
   *
   * @param subscriptionKeys 订阅键数组
   * @param handlersMap key -> handler 映射
   * @returns 取消订阅函数
   */
  private subscribeBatch(subscriptionKeys: string[], handlersMap: Map<string, (data: unknown) => void>): () => void {
    // 存储所有订阅者
    for (const key of subscriptionKeys) {
      if (this.subscriptions.has(key)) {
        this.unsubscribe(key)
      }
      const handler = handlersMap.get(key)
      if (handler) {
        this.subscriptions.set(key, { key, handler: (data, sk) => handler(data) })
      }
    }

    // 发送订阅请求（一次发送所有 keys）
    if (this.connected && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendSubscribeMessage('SUBSCRIBE', subscriptionKeys)
    }

    // 返回批量取消订阅函数
    return () => {
      for (const key of subscriptionKeys) {
        this.unsubscribe(key)
      }
    }
  }

  /**
   * 取消订阅
   *
   * @param subscriptionKey 订阅键
   */
  unsubscribe(subscriptionKey: string): void {
    // 移除订阅者
    this.subscriptions.delete(subscriptionKey)

    // 发送取消订阅请求
    if (this.connected && this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.sendSubscribeMessage('UNSUBSCRIBE', [subscriptionKey])
    }
  }

  /**
   * 发送订阅/取消订阅消息
   */
  private sendSubscribeMessage(type: 'SUBSCRIBE' | 'UNSUBSCRIBE', subscriptions: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }

    const requestId = generateRequestId()

    const message: WSRequestMessage = {
      protocolVersion: PROTOCOL_VERSION,
      type,
      requestId,
      timestamp: Date.now(),
      data: {
        subscriptions,
      },
    }

    this.ws.send(JSON.stringify(message))
  }

  /**
   * 获取当前所有订阅
   *
   * @returns 订阅键数组
   */
  getSubscriptions(): string[] {
    return Array.from(this.subscriptions.keys())
  }
}
