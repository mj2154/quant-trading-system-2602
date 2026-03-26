/**
 * 账户数据转换器
 *
 * 负责将币安API原始数据转换为UI显示模型。
 * 遵循不可变更新原则，每次转换返回新对象。
 */

import type {
  SpotAccountDetail,
  SpotAccountUpdate,
  SpotBalanceUpdateEvent,
  FuturesAccountDetail,
  FuturesAccountUpdate,
} from '../types/api'
import type {
  SpotAccountDisplay,
  FuturesAccountDisplay,
  SpotBalanceDisplay,
  FuturesAssetDisplay,
  FuturesPositionDisplay,
} from '../types/display/account-display'

// ==================== 现货账户转换器 ====================

/**
 * 现货余额详情 -> 现货余额显示项
 */
function convertSpotBalance(balance: {
  asset: string
  free?: string
  locked?: string
}): SpotBalanceDisplay {
  const free = parseFloat(balance.free || '0')
  const locked = parseFloat(balance.locked || '0')
  return {
    asset: balance.asset,
    free: balance.free || '0',
    locked: balance.locked || '0',
    total: (free + locked).toFixed(8).replace(/\.?0+$/, ''),
  }
}

/**
 * 现货账户API数据 -> 现货账户显示模型
 *
 * @param apiData - 币安GET /api/v3/account 返回的原始数据
 * @returns 现货账户显示模型
 */
export function convertSpotAccountToDisplay(
  apiData: SpotAccountDetail
): SpotAccountDisplay {
  // 计算USDT总资产(简化版:只统计USDT余额)
  // 完整实现需要获取各币种对USDT的实时价格
  const usdtBalance = apiData.balances?.find(b => b.asset === 'USDT')
  const free = parseFloat(usdtBalance?.free || '0')
  const locked = parseFloat(usdtBalance?.locked || '0')

  // 构建余额列表，只包含有余额的资产
  const balances: SpotBalanceDisplay[] = (apiData.balances || [])
    .map(convertSpotBalance)
    .filter(b => parseFloat(b.total) > 0)
    .sort((a, b) => parseFloat(b.total) - parseFloat(a.total))

  return {
    totalAsset: (free + locked).toFixed(2),
    availableBalance: usdtBalance?.free || '0',
    lockedBalance: usdtBalance?.locked || '0',
    canTrade: apiData.canTrade ?? false,
    canWithdraw: apiData.canWithdraw ?? false,
    canDeposit: apiData.canDeposit ?? false,
    accountType: apiData.accountType || 'SPOT',
    uid: apiData.uid ?? 0,
    brokered: apiData.brokered ?? false,
    requireSelfTradePrevention: apiData.requireSelfTradePrevention ?? false,
    preventSor: apiData.preventSor ?? false,
    makerCommission: apiData.makerCommission ?? 0,
    takerCommission: apiData.takerCommission ?? 0,
    buyerCommission: apiData.buyerCommission ?? 0,
    sellerCommission: apiData.sellerCommission ?? 0,
    commissionRates: apiData.commissionRates
      ? {
          maker: apiData.commissionRates.maker || '0',
          taker: apiData.commissionRates.taker || '0',
          buyer: apiData.commissionRates.buyer || '0',
          seller: apiData.commissionRates.seller || '0',
        }
      : null,
    balances,
    permissions: apiData.permissions || [],
    updateTime: apiData.updateTime || 0,
  }
}

/**
 * 应用现货账户增量更新 (outboundAccountPosition事件)
 *
 * 币安推送: 当账户余额发生变化时推送，包含所有余额
 *
 * @param display - 当前显示模型
 * @param update - WS推送的outboundAccountPosition事件
 * @returns 更新后的显示模型(新对象)
 */
export function applySpotOutboundUpdate(
  display: SpotAccountDisplay,
  update: SpotAccountUpdate
): SpotAccountDisplay {
  // 创建余额列表的副本
  const newBalances = display.balances.map(b => ({ ...b }))

  // 更新余额
  for (const balanceUpdate of update.B || []) {
    const index = newBalances.findIndex(b => b.asset === balanceUpdate.a)
    const free = parseFloat(balanceUpdate.f)
    const locked = parseFloat(balanceUpdate.l)

    if (index >= 0) {
      // 更新现有资产
      newBalances[index] = {
        ...newBalances[index],
        free: balanceUpdate.f,
        locked: balanceUpdate.l,
        total: (free + locked).toFixed(8).replace(/\.?0+$/, ''),
      }
    } else {
      // 添加新资产
      newBalances.push({
        asset: balanceUpdate.a,
        free: balanceUpdate.f,
        locked: balanceUpdate.l,
        total: (free + locked).toFixed(8).replace(/\.?0+$/, ''),
      })
    }
  }

  // 重新计算USDT总资产
  const usdtBalance = newBalances.find(b => b.asset === 'USDT')
  const totalFree = parseFloat(usdtBalance?.free || '0')
  const totalLocked = parseFloat(usdtBalance?.locked || '0')

  return {
    ...display,
    totalAsset: (totalFree + totalLocked).toFixed(2),
    availableBalance: usdtBalance?.free || '0',
    lockedBalance: usdtBalance?.locked || '0',
    balances: newBalances,
    updateTime: update.u,
  }
}

/**
 * 应用现货余额增量更新 (balanceUpdate事件)
 *
 * 币安推送: 充值/提现/转账时推送，包含单个资产变化
 *
 * @param display - 当前显示模型
 * @param update - WS推送的balanceUpdate事件
 * @returns 更新后的显示模型(新对象)
 */
export function applySpotBalanceUpdate(
  display: SpotAccountDisplay,
  update: SpotBalanceUpdateEvent
): SpotAccountDisplay {
  const newBalances = display.balances.map(b => ({ ...b }))
  const delta = parseFloat(update.d)

  const index = newBalances.findIndex(b => b.asset === update.a)

  if (index >= 0) {
    // 更新现有资产
    const currentFree = parseFloat(newBalances[index].free)
    const newFree = currentFree + delta
    const locked = parseFloat(newBalances[index].locked)

    newBalances[index] = {
      ...newBalances[index],
      free: newFree.toFixed(8).replace(/\.?0+$/, ''),
      total: (newFree + locked).toFixed(8).replace(/\.?0+$/, ''),
    }
  } else {
    // 新资产，创建余额记录
    newBalances.push({
      asset: update.a,
      free: update.d,
      locked: '0',
      total: delta.toFixed(8).replace(/\.?0+$/, ''),
    })
  }

  // 重新计算USDT
  const usdtBalance = newBalances.find(b => b.asset === 'USDT')
  const totalFree = parseFloat(usdtBalance?.free || '0')
  const totalLocked = parseFloat(usdtBalance?.locked || '0')

  return {
    ...display,
    totalAsset: (totalFree + totalLocked).toFixed(2),
    availableBalance: usdtBalance?.free || '0',
    lockedBalance: usdtBalance?.locked || '0',
    balances: newBalances,
    updateTime: update.E,
  }
}

// ==================== 期货账户转换器 ====================

/**
 * 期货资产API数据 -> 期货资产显示项
 */
function convertFuturesAsset(
  asset: FuturesAccountDetail['assets'][number]
): FuturesAssetDisplay {
  return {
    asset: asset.asset || '',
    walletBalance: asset.walletBalance || '0',
    unrealizedProfit: asset.unrealizedProfit || '0',
    marginBalance: asset.marginBalance || '0',
    availableBalance: asset.availableBalance || '0',
    maxWithdraw: asset.maxWithdrawAmount || '0',
    crossWalletBalance: asset.crossWalletBalance || '0',
    crossUnrealizedProfit: asset.crossUnrealizedProfit || '0',
    updateTime: asset.updateTime,
  }
}

/**
 * 期货持仓API数据 -> 期货持仓显示项
 *
 * 注意: /fapi/v3/account 返回的持仓数据不包含entryPrice, markPrice, liquidationPrice
 * 这些字段需要通过/fapi/v3/positionRisk单独获取
 */
function convertFuturesPosition(
  position: FuturesAccountDetail['positions'][number]
): FuturesPositionDisplay {
  return {
    symbol: position.symbol || '',
    side: (position.positionSide as 'LONG' | 'SHORT' | 'BOTH') || 'BOTH',
    positionAmt: position.positionAmt || '0',
    unrealizedProfit: position.unrealizedProfit || '0',
    // V3 API不返回以下字段
    entryPrice: '-',
    markPrice: '-',
    liquidationPrice: '-',
    leverage: position.leverage ?? 0,
    isolatedMargin: position.isolatedMargin || '0',
    initialMargin: position.initialMargin || '0',
    maintMargin: position.maintMargin || '0',
    notional: position.notional || '0',
    updateTime: position.updateTime || 0,
  }
}

/**
 * 期货账户API数据 -> 期货账户显示模型
 *
 * @param apiData - 币安GET /fapi/v3/account 返回的原始数据
 * @returns 期货账户显示模型
 */
export function convertFuturesAccountToDisplay(
  apiData: FuturesAccountDetail
): FuturesAccountDisplay {
  return {
    totalWalletBalance: apiData.totalWalletBalance || '0',
    totalUnrealizedProfit: apiData.totalUnrealizedProfit || '0',
    totalMarginBalance: apiData.totalMarginBalance || '0',
    availableBalance: apiData.availableBalance || '0',
    maxWithdrawAmount: apiData.maxWithdrawAmount || '0',
    totalInitialMargin: apiData.totalInitialMargin || '0',
    totalMaintMargin: apiData.totalMaintMargin || '0',
    totalPositionInitialMargin: apiData.totalPositionInitialMargin || '0',
    totalOpenOrderInitialMargin: apiData.totalOpenOrderInitialMargin || '0',
    feeTier: apiData.feeTier ?? 0,
    multiAssetsMargin: apiData.multiAssetsMargin ?? false,
    positionMode: 'oneWay', // API不返回此字段，需要通过ACCOUNT_CONFIG_UPDATE获取
    assets: (apiData.assets || []).map(convertFuturesAsset),
    positions: (apiData.positions || []).map(convertFuturesPosition),
    updateTime: apiData.updateTime || 0,
  }
}

/**
 * 应用期货账户增量更新 (ACCOUNT_UPDATE事件)
 *
 * 币安推送的ACCOUNT_UPDATE事件包含：
 * - a.B: 余额更新列表
 * - a.P: 持仓更新列表
 *
 * 注意：ACCOUNT_UPDATE不包含顶层聚合字段（totalWalletBalance等），
 * 需要根据B[]和P[]计算得出。
 *
 * @param display - 当前显示模型
 * @param update - WS推送的ACCOUNT_UPDATE事件
 * @param leverageMap - 杠杆率映射表 (symbol -> leverage)
 * @returns 更新后的显示模型(新对象)
 */
export function applyFuturesAccountUpdate(
  display: FuturesAccountDisplay,
  update: FuturesAccountUpdate,
  leverageMap: Record<string, number> = {}
): FuturesAccountDisplay {
  const { a } = update
  if (!a) {
    return display
  }

  // 创建资产列表副本
  const newAssets = display.assets.map(a => ({ ...a }))

  // 处理余额更新 (B)
  if (a.B && a.B.length > 0) {
    for (const balanceUpdate of a.B) {
      const index = newAssets.findIndex(asset => asset.asset === balanceUpdate.a)
      if (index >= 0) {
        // 更新现有资产
        // 注意: WS 不推送 availableBalance 和 maxWithdrawAmount，用 cw 作为近似
        newAssets[index] = {
          ...newAssets[index],
          walletBalance: balanceUpdate.wb,
          crossWalletBalance: balanceUpdate.cw,
          availableBalance: balanceUpdate.cw,
          maxWithdraw: balanceUpdate.cw, // WS不推送，用cw作为近似
        }
      } else {
        // 添加新资产
        newAssets.push({
          asset: balanceUpdate.a,
          walletBalance: balanceUpdate.wb,
          unrealizedProfit: '0',
          marginBalance: balanceUpdate.wb,
          availableBalance: balanceUpdate.cw,
          maxWithdraw: balanceUpdate.cw, // WS不推送，用cw作为近似
          crossWalletBalance: balanceUpdate.cw,
          crossUnrealizedProfit: '0',
        })
      }
    }
  }

  // 创建持仓列表副本
  const newPositions = display.positions.map(p => ({ ...p }))

  // 处理持仓更新 (P)
  if (a.P && a.P.length > 0) {
    for (const positionUpdate of a.P) {
      const index = newPositions.findIndex(p => p.symbol === positionUpdate.s)
      if (index >= 0) {
        // 更新现有持仓
        // 注意: WS只推送pa(持仓数量)和up(未实现盈亏)
        // entryPrice/markPrice/liquidationPrice保留原值
        newPositions[index] = {
          ...newPositions[index],
          positionAmt: positionUpdate.pa,
          unrealizedProfit: positionUpdate.up || '0',
          updateTime: update.T,
        }
      } else {
        // 新增持仓
        // WS推送新增持仓时，说明用户刚开仓，需要创建完整记录
        // leverage从leverageMap获取，如果没有则默认为1
        const positionAmt = parseFloat(positionUpdate.pa || '0')
        const entryPrice = parseFloat(positionUpdate.ep || '0')
        const leverage = leverageMap[positionUpdate.s] ?? 1

        newPositions.push({
          symbol: positionUpdate.s,
          side: (positionUpdate.ps as 'LONG' | 'SHORT' | 'BOTH') || 'BOTH',
          positionAmt: positionUpdate.pa,
          unrealizedProfit: positionUpdate.up || '0',
          entryPrice: positionUpdate.ep || '-',
          markPrice: '-',
          liquidationPrice: '-',
          leverage,
          isolatedMargin: positionUpdate.iw || '0',
          initialMargin: '0',
          maintMargin: '0',
          notional: positionAmt * entryPrice > 0
            ? (positionAmt * entryPrice).toFixed(8)
            : '0',
          updateTime: update.T,
        })
      }
    }
  }

  // 重新计算聚合字段
  // totalWalletBalance: 从assets中获取USDT的钱包余额
  const usdtAsset = newAssets.find(a => a.asset === 'USDT')
  const totalWalletBalance = usdtAsset?.walletBalance || '0'

  // totalUnrealizedProfit: 累加所有持仓的未实现盈亏
  const totalUnrealizedProfit = newPositions.reduce(
    (sum, p) => sum + parseFloat(p.unrealizedProfit || '0'),
    0
  )

  // totalMarginBalance = totalWalletBalance + totalUnrealizedProfit
  const totalMarginBalance = parseFloat(totalWalletBalance) + totalUnrealizedProfit

  // availableBalance: 从USDT资产获取
  const availableBalance = usdtAsset?.availableBalance || '0'

  // maxWithdrawAmount: 从USDT资产获取
  const maxWithdrawAmount = usdtAsset?.maxWithdraw || '0'

  return {
    ...display,
    totalWalletBalance,
    totalUnrealizedProfit: totalUnrealizedProfit.toFixed(8),
    totalMarginBalance: totalMarginBalance.toFixed(8),
    availableBalance,
    maxWithdrawAmount,
    assets: newAssets,
    positions: newPositions,
    updateTime: update.T,
  }
}
