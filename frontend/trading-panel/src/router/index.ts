import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

export const MODULE_CONFIG = {
  'kline-chart': { title: 'K线图表', color: '#e74c3c', keepAlive: true },
  'module-b': { title: 'Module B', color: '#2ecc71', keepAlive: true },
  'module-c': { title: 'Module C', color: '#3498db', keepAlive: true },
  'alert-dashboard': { title: '告警管理', color: '#e67e22', keepAlive: true },
  'account-dashboard': { title: '账户信息', color: '#9b59b6', keepAlive: true },
  'alert-test': { title: '告警测试', color: '#f39c12', keepAlive: true },
  'trading-dashboard': { title: '交易面板', color: '#00cec9', keepAlive: true },
} as const

export type ModuleType = keyof typeof MODULE_CONFIG

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/kline-chart' },
  {
    path: '/kline-chart',
    name: 'KlineChart',
    component: () => import('../views/KLineChart.vue'),
    meta: { title: 'K线图表', color: '#e74c3c', keepAlive: true },
  },
  {
    path: '/module-b',
    name: 'ModuleB',
    component: () => import('../views/ModuleB.vue'),
    meta: { title: 'Module B', color: '#2ecc71', keepAlive: true },
  },
  {
    path: '/module-c',
    name: 'ModuleC',
    component: () => import('../views/ModuleC.vue'),
    meta: { title: 'Module C', color: '#3498db', keepAlive: true },
  },
  {
    path: '/alert-dashboard',
    name: 'AlertDashboard',
    component: () => import('../views/AlertDashboard.vue'),
    meta: { title: '告警管理', color: '#e67e22', keepAlive: true },
  },
  {
    path: '/account-dashboard',
    name: 'AccountDashboard',
    component: () => import('../views/AccountDashboard.vue'),
    meta: { title: '账户信息', color: '#9b59b6', keepAlive: true },
  },
  {
    path: '/alert-test',
    name: 'AlertTest',
    component: () => import('../views/AlertTest.vue'),
    meta: { title: '告警测试', color: '#f39c12', keepAlive: true },
  },
  {
    path: '/trading-dashboard',
    name: 'TradingDashboard',
    component: () => import('../views/TradingDashboard.vue'),
    meta: { title: '交易面板', color: '#00cec9', keepAlive: true },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export const navItems = Object.entries(MODULE_CONFIG).map(([path, config]) => ({
  path: `/${path}`,
  title: config.title,
  color: config.color,
}))

export const keepAliveNames = routes
  .filter((r): r is RouteRecordRaw & { name: string } => !!r.name && !!r.meta?.keepAlive)
  .map(r => r.name)

export default router
