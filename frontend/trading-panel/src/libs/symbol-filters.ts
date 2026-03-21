/**
 * 币安交易对过滤器配置
 *
 * 存储常用交易对的过滤器参数，用于前端订单参数校验和格式化
 * 数据来源: 币安 exchangeInfo API
 *
 * @see https://developers.binance.com/docs/binance-spot-api-docs/filters
 */

/**
 * 交易对过滤器配置
 */
export interface SymbolFilters {
  /** 数量过滤器 */
  lotSize: {
    minQty: number
    maxQty: number
    stepSize: number
  }
  /** 价格过滤器 */
  priceFilter: {
    minPrice: number
    maxPrice: number
    tickSize: number
  }
  /** 最小名义价值过滤器 */
  minNotional: {
    minNotional: number
  }
}

/**
 * 常用交易对过滤器配置
 * 数据基于 BTCUSDT 和 ETHUSDT，其他交易对可按需添加
 */
export const SYMBOL_FILTERS: Record<string, SymbolFilters> = {
  BTCUSDT: {
    lotSize: {
      minQty: 0.00001,
      maxQty: 9000,
      stepSize: 0.00001,
    },
    priceFilter: {
      minPrice: 0.01,
      maxPrice: 1000000,
      tickSize: 0.01,
    },
    minNotional: {
      minNotional: 5,
    },
  },
  ETHUSDT: {
    lotSize: {
      minQty: 0.0001,
      maxQty: 9000,
      stepSize: 0.0001,
    },
    priceFilter: {
      minPrice: 0.01,
      maxPrice: 100000,
      tickSize: 0.01,
    },
    minNotional: {
      minNotional: 5,
    },
  },
  BNBUSDT: {
    lotSize: {
      minQty: 0.001,
      maxQty: 9000,
      stepSize: 0.001,
    },
    priceFilter: {
      minPrice: 0.01,
      maxPrice: 100000,
      tickSize: 0.01,
    },
    minNotional: {
      minNotional: 5,
    },
  },
  SOLUSDT: {
    lotSize: {
      minQty: 0.001,
      maxQty: 9000,
      stepSize: 0.001,
    },
    priceFilter: {
      minPrice: 0.01,
      maxPrice: 10000,
      tickSize: 0.01,
    },
    minNotional: {
      minNotional: 5,
    },
  },
  XRPUSDT: {
    lotSize: {
      minQty: 0.1,
      maxQty: 900000,
      stepSize: 0.1,
    },
    priceFilter: {
      minPrice: 0.0001,
      maxPrice: 10000,
      tickSize: 0.0001,
    },
    minNotional: {
      minNotional: 5,
    },
  },
}

/**
 * 默认过滤器配置（用于未知交易对）
 * 保守地使用较小的 stepSize 和 tickSize
 */
export const DEFAULT_FILTERS: SymbolFilters = {
  lotSize: {
    minQty: 0.00001,
    maxQty: 9000,
    stepSize: 0.00001,
  },
  priceFilter: {
    minPrice: 0.0001,
    maxPrice: 1000000,
    tickSize: 0.0001,
  },
  minNotional: {
    minNotional: 5,
  },
}

/**
 * 获取交易对的过滤器配置
 * 如果找不到精确匹配，返回默认配置
 */
export function getSymbolFilters(symbol: string): SymbolFilters {
  // 移除 BINANCE: 前缀和 .PERP 后缀
  const cleanSymbol = symbol
    .replace(/^BINANCE:/i, '')
    .replace(/\.PERP$/i, '')
    .toUpperCase()

  return SYMBOL_FILTERS[cleanSymbol] || DEFAULT_FILTERS
}
