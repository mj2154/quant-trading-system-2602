/**
 * 统一WebSocket客户端 - 导出入口
 *
 * 提供:
 * - WSClient 核心类
 * - 类型定义
 * - 便捷的API封装
 */

export { WSClient } from './WSClient'
export * from './types'

// 便捷: 创建默认配置的客户端
import { WSClient } from './WSClient'
import type { WSClientOptions } from './types'

/**
 * 创建默认配置的WS客户端
 *
 * @param options 可选的配置选项
 * @returns WSClient实例
 */
export function createWSClient(options?: Partial<WSClientOptions>): WSClient {
  return new WSClient({
    url: options?.url || getDefaultWSUrl(),
    autoReconnect: options?.autoReconnect ?? true,
    reconnectInterval: options?.reconnectInterval ?? 3000,
    requestTimeout: options?.requestTimeout ?? 30000,
  })
}

/**
 * 获取默认的WebSocket URL
 */
function getDefaultWSUrl(): string {
  // 检查环境变量或使用默认值
  const wsHost = import.meta.env?.VITE_WS_HOST || 'localhost:8000'
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${wsHost}/ws`
}

// ==================== 导出所有API函数 ====================

export { createWSClient as default }
