<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { NGrid, NGridItem } from 'naive-ui'
import OrderForm from '../components/trading/OrderForm.vue'
import OrderList from '../components/trading/OrderList.vue'
import OrderDetail from '../components/trading/OrderDetail.vue'
import { useTradingStore } from '../stores/trading-store'

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
  const url = `${wsProtocol}//${host || 'localhost:8000'}/ws/trading`

  try {
    ws = new WebSocket(url)

    ws.onopen = () => {
      log('log', 'WebSocket connected')
      // Subscribe to order updates
      ws?.send(
        JSON.stringify({
          type: 'SUBSCRIBE',
          subscriptions: ['TRADING:ORDER'],
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
</script>

<template>
  <div class="trading-dashboard module-view">
    <div class="dashboard-header">
      <h1 class="dashboard-title">交易面板</h1>
      <p class="dashboard-subtitle">实时订单管理与交易执行</p>
    </div>

    <NGrid :cols="24" :x-gap="20" :y-gap="20" responsive="screen" item-responsive>
      <!-- Order Form -->
      <NGridItem :span="24" :md="{ span: 10 }" :lg="{ span: 8 }">
        <div class="card-wrapper">
          <OrderForm />
        </div>
      </NGridItem>

      <!-- Order List -->
      <NGridItem :span="24" :md="{ span: 14 }" :lg="{ span: 16 }">
        <div class="card-wrapper">
          <OrderList />
        </div>
      </NGridItem>
    </NGrid>

    <!-- Order Detail Modal -->
    <OrderDetail
      v-if="tradingStore.currentOrder"
      :order="tradingStore.currentOrder"
      @close="tradingStore.setCurrentOrder(null)"
    />
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

/* Card Wrapper */
.card-wrapper {
  background: rgba(30, 41, 59, 0.6);
  border-radius: 16px;
  border: 1px solid rgba(245, 158, 11, 0.15);
  backdrop-filter: blur(10px);
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.3),
    0 2px 4px -1px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
}

.card-wrapper:hover {
  border-color: rgba(245, 158, 11, 0.3);
  box-shadow:
    0 8px 25px -5px rgba(0, 0, 0, 0.4),
    0 4px 10px -5px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .trading-dashboard {
    padding: 16px;
  }

  .dashboard-title {
    font-size: 22px;
  }

  .card-wrapper {
    border-radius: 12px;
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
