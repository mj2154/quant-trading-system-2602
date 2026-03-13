/**
 * Trading Types - WebSocket消息类型定义
 * Based on design document: docs/frontend/design/TRADING.md
 *
 * 注意：订单相关类型已移至 types/api/order.ts
 * 此文件仅保留 WebSocket 消息类型定义
 */

// ==================== WebSocket 消息类型 ====================

/**
 * 交易相关WebSocket消息类型
 * 对应后端 WS 协议消息类型
 */
export type TradingMessageType =
  | 'CREATE_ORDER'
  | 'GET_ORDER'
  | 'LIST_ORDERS'
  | 'CANCEL_ORDER'
  | 'GET_OPEN_ORDERS'
  | 'ORDER_DATA'
  | 'ORDER_LIST_DATA'
  | 'ORDER_UPDATE'
  | 'ERROR'

/**
 * WebSocket交易消息结构
 * 对应 WS 协议消息格式
 */
export interface TradingMessage {
  type: TradingMessageType
  requestId?: string
  data?: unknown
  error?: string
}
