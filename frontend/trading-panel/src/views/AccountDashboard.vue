<script setup lang="ts">
import { onMounted, ref, h, computed } from 'vue'
import { NCard, NStatistic, NGrid, NGi, NSpin, NEmpty, NTag, NDataTable, NButton, NIcon, NProgress, NTabs, NTabPane, NTooltip, NBadge, NAlert, NCollapse, NCollapseItem, NAvatar, NSpace, NDivider } from 'naive-ui'
import { RefreshOutline, WalletOutline, TrendingUpOutline, TrendingDownOutline, ShieldCheckmarkOutline, AlertCircleOutline, SwapHorizontalOutline, PersonOutline, KeyOutline, FlameOutline, CashOutline, DocumentTextOutline, GitNetworkOutline, TimeOutline, StatsChartOutline, PricetagOutline, EllipseOutline } from '@vicons/ionicons5'
import { useAccountStore } from '../stores/account-store'

// Store
const store = useAccountStore()

// 当前选中的账户类型
const activeAccountType = ref<'spot' | 'futures'>('futures')

// 格式化数字
function formatNumber(value: string | number | undefined, decimals: number = 2): string {
  if (value === undefined || value === null) return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'
  return num.toFixed(decimals)
}

// 格式化大额数字（带K/M/B后缀）
function formatLargeNumber(value: string | number | undefined): string {
  if (value === undefined || value === null) return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'
  if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B'
  if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M'
  if (num >= 1e3) return (num / 1e3).toFixed(2) + 'K'
  return num.toFixed(2)
}

// 格式化百分比
function formatPercent(value: string | number | undefined): string {
  if (value === undefined || value === null) return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'
  return (num * 100).toFixed(2) + '%'
}

// 格式化币安手续费率 (basis points -> 百分比)
// 币安返回的 makerCommission/takerCommission 是整数 (basis points)
// 例如: 15 = 0.0015% = 0.015‰
function formatCommissionRate(value: string | number | undefined): string {
  if (value === undefined || value === null) return '-'
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(num)) return '-'
  // basis points 转换为百分比: 15 / 10000 = 0.0015%
  return (num / 10000).toFixed(4) + '%'
}

// 格式化 commission_rates 中的字符串费率
function formatStringRate(value: string | undefined): string {
  if (!value) return '-'
  const num = parseFloat(value)
  if (isNaN(num)) return '-'
  return (num * 100).toFixed(4) + '%'
}

// 格式化时间
function formatTime(timestamp: number | undefined): string {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString()
}

// 计算收益率
function calculateROE(unrealizedPnl: string | undefined, initialMargin: string | undefined): string {
  if (!unrealizedPnl || !initialMargin) return '-'
  const pnl = parseFloat(unrealizedPnl)
  const margin = parseFloat(initialMargin)
  if (margin === 0) return '0.00%'
  return ((pnl / margin) * 100).toFixed(2) + '%'
}

// 计算盈亏颜色
function getPnlClass(value: string | undefined): string {
  if (!value) return ''
  const num = parseFloat(value)
  if (num > 0) return 'pnl-positive'
  if (num < 0) return 'pnl-negative'
  return ''
}

// 计算保证金率 (风险指标)
function calculateMarginRate(maintMargin: string | undefined, marginBalance: string | undefined): string {
  if (!maintMargin || !marginBalance) return '-'
  const maint = parseFloat(maintMargin)
  const balance = parseFloat(marginBalance)
  if (balance === 0) return '-'
  return ((maint / balance) * 100).toFixed(2) + '%'
}

// 切换账户类型
function switchAccountType(type: 'spot' | 'futures') {
  activeAccountType.value = type
}

// 刷新数据
async function handleRefresh() {
  await store.refreshAccounts()
}

// 组件挂载时初始化
onMounted(() => {
  store.initialize()
  store.refreshAccounts()
})

// 计算账户风险等级
const riskLevel = computed(() => {
  if (!store.futuresAccount) return { level: 'unknown', label: '未知', color: 'default' as const }
  const totalPnl = parseFloat(store.futuresAccount.total_unrealized_profit || '0')
  const totalMargin = parseFloat(store.futuresAccount.total_initial_margin || '1')
  const rate = totalPnl / totalMargin

  if (rate > 0.2) return { level: 'low', label: '低风险', color: 'success' as const }
  if (rate > 0) return { level: 'medium', label: '适中', color: 'warning' as const }
  if (rate > -0.1) return { level: 'high', label: '高风险', color: 'error' as const }
  return { level: 'critical', label: '危险', color: 'error' as const }
})

// 期货持仓表格列 - 完整数据
// 注意: /fapi/v3/account 返回的字段有限，完整数据需要 /fapi/v3/positionRisk
const futuresPositionColumns: any[] = [
  { title: '交易对', key: 'symbol', width: 110, fixed: 'left' },
  { title: '方向', key: 'side', width: 75, render: (row: any) => h(NTag, { type: row.side === 'long' ? 'success' : row.side === 'short' ? 'error' : 'info', size: 'small' }, { default: () => row.side.toUpperCase() }) },
  { title: '数量', key: 'amount', width: 95, render: (row: any) => formatNumber(row.amount, 4) },
  { title: '开仓价', key: 'entryPrice', width: 95, render: (row: any) => row.entryPrice === '-' ? h('span', { class: 'text-muted' }, '-') : formatNumber(row.entryPrice) },
  { title: '标记价', key: 'markPrice', width: 95, render: (row: any) => row.markPrice === '-' ? h('span', { class: 'text-muted' }, '-') : formatNumber(row.markPrice) },
  { title: '强平价', key: 'liquidationPrice', width: 95, render: (row: any) => row.liquidationPrice === '-' ? h('span', { class: 'text-muted' }, '-') : h('span', { class: parseFloat(row.liquidationPrice || '0') ? '' : 'text-muted' }, formatNumber(row.liquidationPrice)) },
  { title: '杠杆', key: 'leverage', width: 65, render: (row: any) => row.leverage ? h(NTag, { type: parseInt(row.leverage) > 50 ? 'error' : parseInt(row.leverage) > 20 ? 'warning' : 'info', size: 'small' }, { default: () => row.leverage + 'x' }) : '-' },
  { title: '模式', key: 'isolated', width: 70, render: (row: any) => row.isIsolated ? h(NTag, { type: 'warning', size: 'small' }, { default: () => '逐仓' }) : h(NTag, { type: 'info', size: 'small' }, { default: () => '全仓' }) },
  { title: '名义价值', key: 'notional', width: 110, render: (row: any) => formatLargeNumber(row.notional) },
  { title: '保证金', key: 'margin', width: 95, render: (row: any) => formatNumber(row.margin) },
  { title: '未实现盈亏', key: 'unrealizedPnl', width: 110, render: (row: any) => h('span', { class: getPnlClass(row.unrealizedPnl) }, (parseFloat(row.unrealizedPnl) > 0 ? '+' : '') + formatNumber(row.unrealizedPnl)) },
  { title: '收益率', key: 'roe', width: 85, render: (row: any) => {
    const roe = calculateROE(row.unrealizedPnl, row.margin)
    return h('span', { class: getPnlClass(row.unrealizedPnl) }, roe)
  }},
]

// 现货余额表格列
const spotBalanceColumns = [
  { title: '资产', key: 'asset', width: 80, render: (row: any) => h('div', { class: 'asset-cell' }, [
    h(NAvatar, { size: 24, style: { backgroundColor: getAssetColor(row.asset) }, round: true }, { default: () => row.asset[0] }),
    h('span', { style: 'margin-left: 8px' }, row.asset)
  ]) },
  { title: '可用', key: 'free', width: 150, render: (row: any) => formatNumber(row.free, 6) },
  { title: '锁定', key: 'locked', width: 150, render: (row: any) => formatNumber(row.locked, 6) },
  { title: '总计', key: 'total', width: 150, render: (row: any) => formatNumber(row.total, 6) },
  { title: '估值(USDT)', key: 'usdt_value', width: 120, render: (row: any) => row.asset === 'USDT' ? formatNumber(row.total) : '-' },
]

// 期货资产表格列
const futuresAssetColumns = [
  { title: '资产', key: 'asset', width: 80 },
  { title: '钱包余额', key: 'wallet_balance', width: 120, render: (row: any) => formatNumber(row.wallet_balance) },
  { title: '未实现盈亏', key: 'unrealized_profit', width: 120, render: (row: any) => h('span', { class: getPnlClass(row.unrealized_profit) }, (parseFloat(row.unrealized_profit) > 0 ? '+' : '') + formatNumber(row.unrealized_profit)) },
  { title: '保证金余额', key: 'margin_balance', width: 120, render: (row: any) => formatNumber(row.margin_balance) },
  { title: '可用余额', key: 'available_balance', width: 120, render: (row: any) => h('span', { class: 'text-success' }, formatNumber(row.available_balance)) },
  { title: '初始保证金', key: 'initial_margin', width: 120, render: (row: any) => formatNumber(row.initial_margin) },
  { title: '维持保证金', key: 'maint_margin', width: 120, render: (row: any) => formatNumber(row.maint_margin) },
  { title: '可提现', key: 'max_withdraw_amount', width: 100, render: (row: any) => formatNumber(row.max_withdraw_amount) },
  { title: '全仓余额', key: 'cross_wallet_balance', width: 120, render: (row: any) => formatNumber(row.cross_wallet_balance) },
  { title: '联合保证金', key: 'margin_available', width: 90, render: (row: any) => row.margin_available ? h(NTag, { type: 'success', size: 'small' }, { default: () => '可用' }) : h(NTag, { type: 'default', size: 'small' }, { default: () => '不可用' }) },
]

// 资产颜色映射
function getAssetColor(asset: string): string {
  const colors: Record<string, string> = {
    'USDT': '#26A17B',
    'BTC': '#F7931A',
    'ETH': '#627EEA',
    'BNB': '#F3BA2F',
    'BUSD': '#F0B90B',
    'SOL': '#9945FF',
    'XRP': '#23292F',
    'ADA': '#0033AD',
    'DOGE': '#C2A633',
    'DOT': '#E6007A',
  }
  return colors[asset] || '#6B7280'
}

// 总权益计算
const totalEquity = computed(() => {
  if (!store.futuresAccount) return '0'
  const wallet = parseFloat(store.futuresAccount.total_wallet_balance || '0')
  const pnl = parseFloat(store.futuresAccount.total_unrealized_profit || '0')
  return (wallet + pnl).toFixed(2)
})
</script>

<template>
  <div class="account-dashboard">
    <!-- 顶部统计栏 - 专业金融风格 -->
    <div class="stats-bar">
      <!-- 期货账户统计 -->
      <div class="stat-item futures" @click="switchAccountType('futures')" :class="{ active: activeAccountType === 'futures' }">
        <div class="stat-icon futures">
          <NIcon size="20"><TrendingUpOutline /></NIcon>
        </div>
        <div class="stat-content">
          <div class="stat-header">
            <span class="stat-label">合约账户 (USDT)</span>
            <NTag type="success" size="small">U本位</NTag>
          </div>
          <div class="stat-value-row">
            <span class="stat-value-lg">{{ store.futuresLoading ? '加载中...' : formatNumber(totalEquity) }}</span>
            <span class="stat-unit">USDT</span>
          </div>
          <div class="stat-metrics">
            <div class="metric">
              <span class="metric-label">未实现盈亏</span>
              <span class="metric-value" :class="getPnlClass(store.futuresAccount?.total_unrealized_profit)">
                {{ store.futuresAccount?.total_unrealized_profit && parseFloat(store.futuresAccount.total_unrealized_profit) > 0 ? '+' : '' }}{{ formatNumber(store.futuresAccount?.total_unrealized_profit) }}
              </span>
            </div>
            <div class="metric">
              <span class="metric-label">持仓</span>
              <span class="metric-value">{{ store.futuresOverview?.positionCount || 0 }}</span>
            </div>
          </div>
        </div>
        <div class="stat-side">
          <div class="side-item">
            <span class="side-label">可用</span>
            <span class="side-value">{{ formatNumber(store.futuresAccount?.available_balance) }}</span>
          </div>
          <div class="side-item">
            <span class="side-label">保证金</span>
            <span class="side-value">{{ formatNumber(store.futuresAccount?.total_initial_margin) }}</span>
          </div>
        </div>
      </div>

      <!-- 现货账户统计 -->
      <div class="stat-item spot" @click="switchAccountType('spot')" :class="{ active: activeAccountType === 'spot' }">
        <div class="stat-icon spot">
          <NIcon size="20"><WalletOutline /></NIcon>
        </div>
        <div class="stat-content">
          <div class="stat-header">
            <span class="stat-label">现货账户</span>
            <NTag :type="store.spotAccount?.can_trade ? 'success' : 'warning'" size="small">{{ store.spotAccount?.account_type || '标准账户' }}</NTag>
          </div>
          <div class="stat-value-row">
            <span class="stat-value-lg">{{ store.spotLoading ? '加载中...' : store.spotBalances.length }}</span>
            <span class="stat-unit">资产</span>
          </div>
          <div class="stat-metrics">
            <div class="metric">
              <span class="metric-label">USDT可用</span>
              <span class="metric-value">{{ formatNumber(store.spotOverview?.availableBalance) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">费率(M/T)</span>
              <span class="metric-value">{{ formatStringRate(store.spotAccount?.commission_rates?.maker) }} / {{ formatStringRate(store.spotAccount?.commission_rates?.taker) }}</span>
            </div>
          </div>
        </div>
        <div class="stat-side">
          <div class="side-item">
            <span class="side-label">权限</span>
            <div class="side-badges">
              <NTag v-if="store.spotAccount?.can_trade" type="success" size="tiny">交易</NTag>
              <NTag v-if="store.spotAccount?.can_deposit" type="info" size="tiny">充值</NTag>
              <NTag v-if="store.spotAccount?.can_withdraw" type="warning" size="tiny">提现</NTag>
            </div>
          </div>
        </div>
      </div>

      <!-- 刷新按钮 -->
      <div class="refresh-section">
        <NButton quaternary circle @click="handleRefresh" :loading="store.spotLoading || store.futuresLoading">
          <template #icon>
            <NIcon><RefreshOutline /></NIcon>
          </template>
        </NButton>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="dashboard-content">
      <!-- 加载状态 -->
      <NSpin v-if="store.spotLoading || store.futuresLoading" size="medium" class="loading-spinner" />

      <!-- 期货账户详情 -->
      <div v-else-if="activeAccountType === 'futures'" class="account-detail">
        <!-- 第一行：核心指标卡片 -->
        <div class="metrics-row">
          <!-- 总权益卡片 -->
          <NCard class="metric-card">
            <div class="metric-card-header">
              <NIcon size="16"><CashOutline /></NIcon>
              <span>总权益 (Total Equity)</span>
            </div>
            <div class="metric-card-value primary">
              {{ formatNumber(totalEquity) }} <span class="unit">USDT</span>
            </div>
            <div class="metric-card-footer">
              <div class="metric-detail">
                <span class="label">钱包余额</span>
                <span class="value">{{ formatNumber(store.futuresAccount?.total_wallet_balance) }}</span>
              </div>
              <div class="metric-detail">
                <span class="label">未实现盈亏</span>
                <span class="value" :class="getPnlClass(store.futuresAccount?.total_unrealized_profit)">
                  {{ store.futuresAccount?.total_unrealized_profit && parseFloat(store.futuresAccount.total_unrealized_profit) > 0 ? '+' : '' }}{{ formatNumber(store.futuresAccount?.total_unrealized_profit) }}
                </span>
              </div>
            </div>
          </NCard>

          <!-- 可用资金卡片 -->
          <NCard class="metric-card">
            <div class="metric-card-header">
              <NIcon size="16"><WalletOutline /></NIcon>
              <span>可用资金 (Available)</span>
            </div>
            <div class="metric-card-value success">
              {{ formatNumber(store.futuresAccount?.available_balance) }} <span class="unit">USDT</span>
            </div>
            <div class="metric-card-footer">
              <div class="metric-detail">
                <span class="label">最大可提现</span>
                <span class="value">{{ formatNumber(store.futuresAccount?.max_withdraw_amount) }}</span>
              </div>
              <div class="metric-detail">
                <span class="label">挂单保证金</span>
                <span class="value">{{ formatNumber(store.futuresAccount?.total_open_order_initial_margin) }}</span>
              </div>
            </div>
          </NCard>

          <!-- 保证金状态卡片 -->
          <NCard class="metric-card">
            <div class="metric-card-header">
              <NIcon size="16"><ShieldCheckmarkOutline /></NIcon>
              <span>保证金状态 (Margin)</span>
            </div>
            <div class="metric-card-value">
              {{ formatNumber(store.futuresAccount?.total_margin_balance) }} <span class="unit">USDT</span>
            </div>
            <div class="metric-card-footer">
              <div class="metric-detail">
                <span class="label">初始保证金</span>
                <span class="value">{{ formatNumber(store.futuresAccount?.total_initial_margin) }}</span>
              </div>
              <div class="metric-detail">
                <span class="label">维持保证金</span>
                <span class="value">{{ formatNumber(store.futuresAccount?.total_maint_margin) }}</span>
              </div>
            </div>
          </NCard>

          <!-- 账户信息卡片 -->
          <NCard class="metric-card info-card">
            <div class="metric-card-header">
              <NIcon size="16"><StatsChartOutline /></NIcon>
              <span>账户信息</span>
            </div>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">更新于</span>
                <span class="info-value">{{ formatTime(store.futuresAssets?.[0]?.update_time) }}</span>
              </div>
            </div>
          </NCard>
        </div>

        <!-- 第二行：详细数据 -->
        <div class="detail-row">
          <!-- 持仓列表 -->
          <NCard title="当前持仓 (Positions)" class="detail-card full-width">
            <template #header-extra>
              <NSpace :size="8">
                <NBadge :value="store.futuresPositions.length" type="info" />
                <NTag v-if="store.futuresPositions.length > 0" :type="riskLevel.color" size="small">
                  {{ riskLevel.label }}
                </NTag>
              </NSpace>
            </template>

            <NEmpty v-if="store.futuresPositions.length === 0" description="暂无持仓" />

            <NDataTable
              v-else
              :columns="futuresPositionColumns"
              :data="store.futuresPositions"
              :bordered="false"
              size="small"
              :max-height="350"
              :scroll-x="1300"
              :scroll-y="300"
              :single-line="false"
              striped
            />

            <template #action>
              <div class="card-summary" v-if="store.futuresPositions.length > 0">
                <span>持仓汇总: 名义价值 {{ formatLargeNumber(store.futuresPositions.reduce((sum: number, p: any) => sum + parseFloat(p.notional || '0'), 0)) }} USDT</span>
              </div>
            </template>
          </NCard>
        </div>

        <!-- 第三行：资产详情 -->
        <div class="detail-row">
          <NCard title="资产详情 (Assets)" class="detail-card full-width">
            <template #header-extra>
              <NBadge :value="store.futuresAssets.length" type="info" />
            </template>

            <NEmpty v-if="store.futuresAssets.length === 0" description="暂无资产" />

            <NDataTable
              v-else
              :columns="futuresAssetColumns"
              :data="store.futuresAssets"
              :bordered="false"
              size="small"
              :max-height="300"
              :scroll-x="1100"
              striped
            />
          </NCard>
        </div>
      </div>

      <!-- 现货账户详情 -->
      <div v-else-if="activeAccountType === 'spot'" class="account-detail">
        <!-- 账户概览 -->
        <div class="metrics-row">
          <NCard class="metric-card">
            <div class="metric-card-header">
              <NIcon size="16"><WalletOutline /></NIcon>
              <span>账户信息</span>
            </div>
            <div class="metric-card-value">
              {{ store.spotAccount?.account_type || '标准账户' }}
            </div>
            <div class="account-permissions">
              <NTag v-if="store.spotAccount?.can_trade" type="success" size="small">可交易</NTag>
              <NTag v-if="store.spotAccount?.can_deposit" type="info" size="small">可充值</NTag>
              <NTag v-if="store.spotAccount?.can_withdraw" type="warning" size="small">可提现</NTag>
            </div>
            <div class="metric-card-footer" v-if="store.spotAccount?.uid">
              <span class="label">用户ID: {{ store.spotAccount?.uid }}</span>
            </div>
          </NCard>

          <NCard class="metric-card">
            <div class="metric-card-header">
              <NIcon size="16"><PricetagOutline /></NIcon>
              <span>手续费率 (Maker/Taker)</span>
            </div>
            <div class="metric-card-value">
              {{ formatStringRate(store.spotAccount?.commission_rates?.maker) }} <span class="unit">/</span> {{ formatStringRate(store.spotAccount?.commission_rates?.taker) }}
            </div>
            <div class="metric-card-footer">
              <div class="metric-detail">
                <span class="label">挂单</span>
                <span class="value">{{ formatStringRate(store.spotAccount?.commission_rates?.maker) }}</span>
              </div>
              <div class="metric-detail">
                <span class="label">吃单</span>
                <span class="value">{{ formatStringRate(store.spotAccount?.commission_rates?.taker) }}</span>
              </div>
            </div>
          </NCard>

          <NCard class="metric-card">
            <div class="metric-card-header">
              <NIcon size="16"><SwapHorizontalOutline /></NIcon>
              <span>交易手续费 (Buyer/Seller)</span>
            </div>
            <div class="metric-card-value small">
              买入: {{ formatStringRate(store.spotAccount?.commission_rates?.buyer) }}
            </div>
            <div class="metric-card-value small">
              卖出: {{ formatStringRate(store.spotAccount?.commission_rates?.seller) }}
            </div>
          </NCard>

          <NCard class="metric-card info-card">
            <div class="metric-card-header">
              <NIcon size="16"><DocumentTextOutline /></NIcon>
              <span>账户配置</span>
            </div>
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">经纪商</span>
                <span class="info-value">{{ store.spotAccount?.brokered ? '是' : '否' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">自成交防护</span>
                <span class="info-value">{{ store.spotAccount?.require_self_trade_prevention ? '开启' : '关闭' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">SOR防护</span>
                <span class="info-value">{{ store.spotAccount?.prevent_sor ? '开启' : '关闭' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">更新时间</span>
                <span class="info-value">{{ formatTime(store.spotAccount?.update_time) }}</span>
              </div>
            </div>
          </NCard>
        </div>

        <!-- 详细费率卡片 -->
        <div class="detail-row" v-if="store.spotAccount?.commission_rates">
          <NCard title="详细费率 (Commission Rates)" class="detail-card full-width">
            <div class="commission-rates-grid">
              <div class="rate-item">
                <span class="rate-label">挂单 (Maker)</span>
                <span class="rate-value">{{ formatStringRate(store.spotAccount?.commission_rates?.maker) }}</span>
              </div>
              <div class="rate-item">
                <span class="rate-label">吃单 (Taker)</span>
                <span class="rate-value">{{ formatStringRate(store.spotAccount?.commission_rates?.taker) }}</span>
              </div>
              <div class="rate-item">
                <span class="rate-label">买入 (Buyer)</span>
                <span class="rate-value">{{ formatStringRate(store.spotAccount?.commission_rates?.buyer) }}</span>
              </div>
              <div class="rate-item">
                <span class="rate-label">卖出 (Seller)</span>
                <span class="rate-value">{{ formatStringRate(store.spotAccount?.commission_rates?.seller) }}</span>
              </div>
            </div>
          </NCard>
        </div>

        <!-- 权限列表 -->
        <div class="detail-row" v-if="store.spotAccount?.permissions?.length">
          <NCard title="账户权限 (Permissions)" class="detail-card full-width">
            <NSpace>
              <NTag v-for="perm in store.spotAccount?.permissions" :key="perm" type="info" size="medium">
                {{ perm }}
              </NTag>
            </NSpace>
          </NCard>
        </div>

        <!-- 余额列表 -->
        <div class="detail-row">
          <NCard title="账户余额 (Balances)" class="detail-card full-width">
            <template #header-extra>
              <NBadge :value="store.spotBalances.length" type="info" />
            </template>

            <NEmpty v-if="store.spotBalances.length === 0" description="暂无余额" />

            <NDataTable
              v-else
              :columns="spotBalanceColumns"
              :data="store.spotBalances"
              :bordered="false"
              size="small"
              :max-height="500"
              striped
            />
          </NCard>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.account-dashboard {
  height: 100%;
  padding: 12px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #0f172a;
}

/* 顶部统计栏 */
.stats-bar {
  display: flex;
  gap: 12px;
  padding: 16px;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
}

.stat-item {
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.08);
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 0;
}

.stat-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}

.stat-item.active {
  border-color: rgba(59, 130, 246, 0.5);
  background: rgba(59, 130, 246, 0.08);
}

.stat-item.futures.active {
  border-color: rgba(245, 158, 11, 0.5);
  background: rgba(245, 158, 11, 0.08);
}

.stat-item.spot.active {
  border-color: rgba(16, 185, 129, 0.5);
  background: rgba(16, 185, 129, 0.08);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.05);
  color: #94A3B8;
  flex-shrink: 0;
}

.stat-icon.futures {
  color: #F59E0B;
  background: rgba(245, 158, 11, 0.15);
}

.stat-icon.spot {
  color: #10B981;
  background: rgba(16, 185, 129, 0.15);
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.stat-label {
  font-size: 11px;
  font-weight: 500;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 8px;
}

.stat-value-lg {
  font-size: 24px;
  font-weight: 700;
  font-family: 'Fira Code', 'SF Mono', monospace;
  color: #F8FAFC;
  line-height: 1.2;
}

.stat-unit {
  font-size: 12px;
  color: #64748B;
}

.stat-metrics {
  display: flex;
  gap: 16px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-label {
  font-size: 10px;
  color: #64748B;
}

.metric-value {
  font-size: 12px;
  font-weight: 600;
  color: #94A3B8;
  font-family: 'Fira Code', 'SF Mono', monospace;
}

.stat-side {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-left: 12px;
  border-left: 1px solid rgba(148, 163, 184, 0.1);
}

.side-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.side-label {
  font-size: 9px;
  color: #64748B;
  text-transform: uppercase;
}

.side-value {
  font-size: 13px;
  font-weight: 600;
  color: #E2E8F0;
  font-family: 'Fira Code', 'SF Mono', monospace;
}

.side-badges {
  display: flex;
  gap: 4px;
}

.refresh-section {
  display: flex;
  align-items: center;
  justify-content: center;
  padding-left: 12px;
  margin-left: auto;
  flex-shrink: 0;
}

/* 主内容区 */
.dashboard-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.loading-spinner {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.account-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 指标卡片行 */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.metric-card {
  background: #1e293b;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.metric-card :deep(.n-card__content) {
  padding: 14px;
}

.metric-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 10px;
}

.metric-card-value {
  font-size: 20px;
  font-weight: 700;
  font-family: 'Fira Code', 'SF Mono', monospace;
  color: #F8FAFC;
  line-height: 1.3;
  margin-bottom: 10px;
}

.metric-card-value.primary {
  color: #60a5fa;
}

.metric-card-value.success {
  color: #10B981;
}

.metric-card-value .unit {
  font-size: 12px;
  font-weight: 400;
  color: #64748B;
  margin-left: 2px;
}

.metric-card-value.small {
  font-size: 14px;
  margin-bottom: 4px;
}

.metric-card-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}

.metric-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-detail .label {
  font-size: 10px;
  color: #64748B;
}

.metric-detail .value {
  font-size: 12px;
  font-weight: 600;
  color: #94A3B8;
  font-family: 'Fira Code', 'SF Mono', monospace;
}

.info-card .info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-label {
  font-size: 10px;
  color: #64748B;
}

.info-value {
  font-size: 12px;
  font-weight: 600;
  color: #E2E8F0;
}

/* 费率卡片 */
.commission-rates-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.rate-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
}

.rate-label {
  font-size: 11px;
  color: #94A3B8;
}

.rate-value {
  font-size: 16px;
  font-weight: 600;
  color: #10B981;
  font-family: 'Fira Code', 'SF Mono', monospace;
}

.account-permissions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* 详细数据行 */
.detail-row {
  display: flex;
  gap: 12px;
}

.detail-card {
  background: #1e293b;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.1);
  flex: 1;
}

.detail-card.full-width {
  width: 100%;
}

.detail-card :deep(.n-card-header) {
  padding: 12px 16px;
}

.detail-card :deep(.n-card__content) {
  padding: 12px;
}

.card-summary {
  padding-top: 10px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
  font-size: 11px;
  color: #64748B;
}

/* 盈亏颜色 */
.pnl-positive {
  color: #10B981 !important;
}

.pnl-negative {
  color: #EF4444 !important;
}

.text-success {
  color: #10B981;
}

.text-muted {
  color: #64748B;
}

/* 资产单元格 */
.asset-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 响应式 */
@media (max-width: 1400px) {
  .metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 1100px) {
  .detail-row {
    flex-direction: column;
  }
}

@media (max-width: 900px) {
  .stats-bar {
    flex-wrap: wrap;
  }

  .stat-item {
    min-width: calc(50% - 6px);
  }

  .stat-side {
    display: none;
  }

  .refresh-section {
    width: 100%;
    padding-left: 0;
    margin-left: 0;
    border-left: none;
    padding-top: 8px;
    border-top: 1px solid rgba(148, 163, 184, 0.15);
    justify-content: center;
  }
}

@media (max-width: 600px) {
  .stat-item {
    min-width: 100%;
  }

  .metrics-row {
    grid-template-columns: 1fr;
  }
}
</style>
