/**
 * 数据服务API - 类型化函数封装
 *
 * 将DataService的方法封装为独立函数，方便各页面调用
 *
 * 使用方式:
 * ```typescript
 * import { fetchKlines, fetchQuotes, fetchSpotAccount } from './services/data-service/api'
 *
 * // 获取K线数据
 * const klines = await fetchKlines('BINANCE:BTCUSDT', '60', Date.now() - 86400000, Date.now())
 *
 * // 获取多个交易对的报价
 * const quotes = await fetchQuotes(['BINANCE:BTCUSDT', 'BINANCE:ETHUSDT'])
 *
 * // 获取现货账户
 * const account = await fetchSpotAccount()
 * ```
 */

import { dataService } from './DataService'
import type {
  GetKlinesParams,
  KlineBar,
  QuotesData,
  SpotAccountInfo,
  FuturesAccountInfo,
  AlertConfig,
  SignalRecord,
  Order,
  OrderListData,
  SubscriptionOptions,
  QuotesValue,
  AccountUpdate,
} from '../../types/api'

// ==================== 市场数据API ====================

/**
 * 获取K线数据
 *
 * @param symbol - 交易对 (如 'BINANCE:BTCUSDT')
 * @param interval - K线周期 (如 '1', '5', '60', '1D')
 * @param fromTime - 开始时间戳(毫秒)
 * @param toTime - 结束时间戳(毫秒)
 * @param limit - 数量限制(默认500)
 * @returns K线Bar数组
 */
export async function fetchKlines(
  symbol: string,
  interval: string,
  fromTime: number,
  toTime: number,
  limit = 500
): Promise<KlineBar[]> {
  const params: GetKlinesParams = {
    symbol,
    interval,
    fromTime,
    toTime,
    limit,
  }

  const result = await dataService.getKlines(params)
  return result.bars
}

/**
 * 获取多个交易对的报价
 *
 * @param symbols - 交易对列表
 * @returns 报价数据数组
 */
export async function fetchQuotes(symbols: string[]): Promise<QuotesData[]> {
  const result = await dataService.getQuotes(symbols)
  return result.quotes
}

/**
 * 获取单个交易对的报价
 *
 * @param symbol - 交易对
 * @returns 报价数据
 */
export async function fetchQuote(symbol: string): Promise<QuotesData | null> {
  const quotes = await fetchQuotes([symbol])
  return quotes[0] || null
}

// ==================== 账户数据API ====================

/**
 * 获取现货账户信息
 *
 * @returns 现货账户信息
 */
export async function fetchSpotAccount(): Promise<SpotAccountInfo> {
  return dataService.getSpotAccount()
}

/**
 * 获取期货账户信息
 *
 * @returns 期货账户信息
 */
export async function fetchFuturesAccount(): Promise<FuturesAccountInfo> {
  return dataService.getFuturesAccount()
}

/**
 * 获取账户信息（自动判断类型）
 *
 * @param type - 账户类型 'spot' | 'futures'
 * @returns 账户信息
 */
export async function fetchAccount(type: 'spot' | 'futures'): Promise<SpotAccountInfo | FuturesAccountInfo> {
  if (type === 'spot') {
    return fetchSpotAccount()
  }
  return fetchFuturesAccount()
}

// ==================== 告警管理API ====================

/**
 * 获取告警配置列表
 *
 * @param page - 页码(默认1)
 * @param pageSize - 每页数量(默认20)
 * @returns 告警配置数组
 */
export async function fetchAlertConfigs(page = 1, pageSize = 20): Promise<AlertConfig[]> {
  return dataService.listAlertConfigs(page, pageSize)
}

// ==================== 信号管理API ====================

/**
 * 获取信号列表
 *
 * @param params - 查询参数
 * @returns 信号记录数组
 */
export async function fetchSignals(params?: {
  page?: number
  pageSize?: number
  symbol?: string
  strategyType?: string
  interval?: string
  signalValue?: boolean
  fromTime?: number
  toTime?: number
}): Promise<SignalRecord[]> {
  return dataService.listSignals(params)
}

// ==================== 订单管理API ====================

/**
 * 获取订单列表
 *
 * @param params - 查询参数
 * @returns 订单列表数据
 */
export async function fetchOrders(params?: {
  symbol?: string
  status?: string
  startTime?: number
  endTime?: number
  limit?: number
}): Promise<OrderListData> {
  return dataService.listOrders(params)
}

/**
 * 获取当前挂单
 *
 * @param symbol - 交易对(可选)
 * @returns 订单列表数据
 */
export async function fetchOpenOrders(symbol?: string): Promise<OrderListData> {
  return dataService.getOpenOrders(symbol)
}

/**
 * 获取订单详情
 *
 * @param symbol - 交易对
 * @param orderId - 订单ID
 * @returns 订单详情
 */
export async function fetchOrder(symbol: string, orderId: number): Promise<Order> {
  return dataService.getOrder({ symbol, orderId })
}

// ==================== 订阅API ====================

/**
 * 订阅实时数据
 *
 * @param subscriptionKey - 订阅键
 * @param handler - 数据回调
 * @returns 取消订阅函数
 */
export function subscribeTo(
  subscriptionKey: string,
  handler: (data: unknown, subscriptionKey?: string) => void
): () => void {
  return dataService.subscribe(subscriptionKey, handler)
}

/**
 * 取消订阅
 *
 * @param subscriptionKey - 订阅键
 */
export function unsubscribeFrom(subscriptionKey: string): void {
  dataService.unsubscribe(subscriptionKey)
}

/**
 * 获取当前所有订阅
 *
 * @returns 订阅键数组
 */
export function getCurrentSubscriptions(): string[] {
  return dataService.getSubscriptions()
}

// ==================== 类型安全订阅API ====================

/**
 * 订阅K线实时数据
 *
 * @param symbol - 交易对 (如 'BINANCE:BTCUSDT')
 * @param interval - K线周期 (如 '1', '5', '60', '1D')
 * @param callback - 数据回调
 * @param options - 订阅选项
 * @returns 取消订阅函数
 */
export function subscribeKline(
  symbol: string,
  interval: string,
  callback: (bar: KlineBar, subscriptionKey: string) => void,
  options?: SubscriptionOptions
): () => void {
  return dataService.subscribeKline(symbol, interval, callback, options)
}

/**
 * 订阅报价实时数据
 *
 * @param symbols - 交易对列表
 * @param callback - 数据回调
 * @param options - 订阅选项
 * @returns 取消订阅函数
 */
export function subscribeQuotes(
  symbols: string[],
  callback: (quotes: Map<string, QuotesValue>) => void,
  options?: SubscriptionOptions
): () => void {
  return dataService.subscribeQuotes(symbols, callback, options)
}

/**
 * 订阅账户增量更新
 *
 * @param accountType - 账户类型 'SPOT' | 'FUTURES'
 * @param callback - 数据回调
 * @param options - 订阅选项
 * @returns 取消订阅函数
 */
export function subscribeAccount(
  accountType: 'SPOT' | 'FUTURES',
  callback: (update: AccountUpdate) => void,
  options?: SubscriptionOptions
): () => void {
  return dataService.subscribeAccount(accountType, callback, options)
}

/**
 * 订阅信号实时推送
 *
 * @param alertId - 告警ID
 * @param callback - 数据回调
 * @param options - 订阅选项
 * @returns 取消订阅函数
 */
export function subscribeSignal(
  alertId: string,
  callback: (signal: SignalRecord) => void,
  options?: SubscriptionOptions
): () => void {
  return dataService.subscribeSignal(alertId, callback, options)
}

/**
 * 批量订阅
 *
 * @param subscriptions - 订阅配置数组
 * @returns 取消所有订阅的函数
 */
export function subscribeBatch(
  subscriptions: Array<{
    key: string
    callback: (data: unknown, subscriptionKey?: string) => void
    options?: SubscriptionOptions
  }>
): () => void {
  return dataService.subscribeBatch(subscriptions)
}

/**
 * 获取订阅信息
 *
 * @param subscriptionKey - 订阅键
 * @returns 订阅信息
 */
export function getSubscriptionInfo(subscriptionKey: string) {
  return dataService.getSubscriptionInfo(subscriptionKey)
}

/**
 * 获取所有订阅信息
 *
 * @returns 订阅信息数组
 */
export function getAllSubscriptionInfos() {
  return dataService.getAllSubscriptionInfos()
}

/**
 * 清空所有订阅
 */
export function clearAllSubscriptions(): void {
  dataService.clearSubscriptions()
}

// ==================== 连接管理API ====================

/**
 * 连接到数据服务
 */
export async function connect(): Promise<void> {
  await dataService.connect()
}

/**
 * 断开连接
 */
export function disconnect(): void {
  dataService.disconnect()
}

/**
 * 获取连接状态
 */
export function isConnected(): boolean {
  return dataService.isConnected
}
