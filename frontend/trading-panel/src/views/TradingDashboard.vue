<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { NGrid, NGridItem, NCard, NTabs, NTabPane } from 'naive-ui'
import { useTradingStore } from '../stores/trading-store'
import SpotOrderForm from '../components/trading/SpotOrderForm.vue'

// Development mode flag
const isDev = import.meta.env.DEV

// Logger utility
function log(level: 'log' | 'error', message: string, ...args: unknown[]) {
  if (level === 'error' || isDev) {
    console[level](`[TradingDashboard] ${message}`, ...args)
  }
}

const tradingStore = useTradingStore()

// WebSocket subscription for order updates
let ws: WebSocket | null = null

function connectWebSocket() {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = import.meta.env.VITE_WS_HOST
  if (!host) {
    if (isDev) {
      log('log', 'VITE_WS_HOST not set, using localhost:8000 for development')
    } else {
      log('error', 'VITE_WS_HOST environment variable is required in production')
      return
    }
  }
  const url = `${wsProtocol}//${host || 'localhost:8000'}/ws`

  try {
    ws = new WebSocket(url)

    ws.onopen = () => {
      log('log', 'WebSocket connected')
      // Subscribe to order updates (遵循 07-websocket-protocol.md 订阅消息格式)
      ws?.send(
        JSON.stringify({
          protocolVersion: '2.0',
          type: 'SUBSCRIBE',
          timestamp: Date.now(),
          data: {
            subscriptions: ['TRADING:ORDER'],
          },
        })
      )
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        if (message.type === 'ORDER_UPDATE') {
          tradingStore.handleOrderUpdate(message.data)
        }
      } catch (e) {
        log('error', 'Failed to parse message:', e)
      }
    }

    ws.onerror = (error) => {
      log('error', 'WebSocket error:', error)
    }

    ws.onclose = () => {
      log('log', 'WebSocket closed')
      ws = null
    }
  } catch (error) {
    log('error', 'Failed to connect WebSocket:', error)
  }
}

onMounted(() => {
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) {
    ws.close()
    ws = null
  }
})

// Order event handlers
function handleOrderSuccess(order: unknown) {
  log('log', 'Order created successfully:', order)
}

function handleOrderError(error: string) {
  log('error', 'Order error:', error)
}
</script>

<template>
  <div class="trading-dashboard module-view">
    <div class="dashboard-header">
      <h1 class="dashboard-title">交易面板</h1>
      <p class="dashboard-subtitle">实时订单管理与交易执行</p>
    </div>

    <!-- 交易面板标签页 -->
    <NTabs type="line" animated>
      <NTabPane name="spot" tab="现货交易">
        <div class="trading-content">
          <NGrid :cols="24" :x-gap="20" :y-gap="20" responsive="screen" item-responsive>
            <!-- 订单表单 -->
            <NGridItem :span="24" :md="8">
              <SpotOrderForm @order-success="handleOrderSuccess" @order-error="handleOrderError" />
            </NGridItem>

            <!-- 订单列表 -->
            <NGridItem :span="24" :md="16">
              <NCard title="当前挂单" class="orders-card">
                <div class="orders-list">
                  <p class="placeholder-text">连接WebSocket后自动显示当前挂单</p>
                </div>
              </NCard>
            </NGridItem>
          </NGrid>
        </div>
      </NTabPane>

      <NTabPane name="futures" tab="合约交易">
        <div class="trading-content">
          <NGrid :cols="24" :x-gap="20" :y-gap="20" responsive="screen" item-responsive>
            <NGridItem :span="24">
              <NCard title="合约交易" class="placeholder-card">
                <p class="placeholder-text">合约交易功能开发中...</p>
              </NCard>
            </NGridItem>
          </NGrid>
        </div>
      </NTabPane>
    </NTabs>
  </div>
</template>

<style scoped>
.trading-dashboard {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F172A 100%);
}

/* Header Styles */
.dashboard-header {
  margin-bottom: 28px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(245, 158, 11, 0.2);
}

.dashboard-title {
  font-family: 'Exo 2', 'Orbitron', sans-serif;
  font-size: 28px;
  font-weight: 600;
  color: #F8FAFC;
  margin: 0;
  letter-spacing: 0.5px;
  text-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
}

.dashboard-subtitle {
  font-size: 14px;
  color: #94A3B8;
  margin: 8px 0 0 0;
  font-weight: 300;
}

/* Placeholder Card */
.placeholder-card {
  background: rgba(30, 41, 59, 0.6);
  border-radius: 16px;
  border: 1px solid rgba(245, 158, 11, 0.15);
  backdrop-filter: blur(10px);
  padding: 48px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.placeholder-text {
  color: #94A3B8;
  font-size: 14px;
  margin-top: 16px;
}

.placeholder-text code {
  background: rgba(245, 158, 11, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
  color: #F59E0B;
}

/* Trading Content */
.trading-content {
  padding-top: 20px;
}

/* Orders Card */
.orders-card {
  background: rgba(30, 41, 59, 0.6);
  border-radius: 12px;
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.orders-list {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .trading-dashboard {
    padding: 16px;
  }

  .dashboard-title {
    font-size: 22px;
  }
}

/* Custom scrollbar */
.trading-dashboard::-webkit-scrollbar {
  width: 8px;
}

.trading-dashboard::-webkit-scrollbar-track {
  background: rgba(15, 23, 42, 0.5);
  border-radius: 4px;
}

.trading-dashboard::-webkit-scrollbar-thumb {
  background: rgba(245, 158, 11, 0.3);
  border-radius: 4px;
}

.trading-dashboard::-webkit-scrollbar-thumb:hover {
  background: rgba(245, 158, 11, 0.5);
}
</style>
