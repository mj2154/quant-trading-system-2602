/**
 * 数据服务模块 - 统一导出入口
 *
 * 使用方式:
 * ```typescript
 * // 方式1: 导入类
 * import { DataService, dataService } from './services/data-service'
 *
 * // 方式2: 导入函数
 * import { fetchKlines, fetchQuotes, fetchSpotAccount } from './services/data-service/api'
 * ```
 */

export { DataService, dataService } from './DataService'
export * from './api'
