# 组件指南

## 核心组件

### 布局组件

| 组件 | 文件 | 说明 |
|------|------|------|
| AppHeader | `src/components/layout/AppHeader.vue` | 应用头部，包含标签页导航 |
| AppContent | `src/components/layout/AppContent.vue` | 内容区域，渲染活动标签页 |

### 业务组件

| 组件 | 文件 | 说明 |
|------|------|------|
| TradingViewChart | `src/components/TradingViewChart/index.vue` | TradingView 金融图表 |
| AccountDashboard | `src/views/AccountDashboard.vue` | 账户仪表盘 |

## 添加新模块

1. 在 `src/views/NewModule.vue` 中创建组件
2. 在 `src/stores/tab-store.ts` 中添加模块配置
3. 在标签页存储中导入并注册

## TradingView 集成

### 组件结构

```
TradingViewChart/
├── index.vue           # 图表主组件
├── composables/
│   └── useTradingView.js  # 管理组件生命周期
├── utils/
│   └── datafeed.js     # Datafeed API 实现
└── library/            # TradingView 库文件
```

### 自定义配置

- 编辑 `src/components/TradingViewChart/composables/useTradingView.js` 调整组件选项
- 在组合式函数中修改默认交易对/周期
- 在初始化代码中调整技术指标

### 默认配置

- **默认交易对**: BINANCE:BTCUSDT
- **默认周期**: 1小时
- **技术指标**: 5EMA、MACD（自动加载）

## 关键修改

### 修改标签页行为

- 编辑 `src/stores/tab-store.ts` 调整标签页管理逻辑
- 更新 `src/components/layout/AppHeader.vue` 调整标签页 UI
- 修改 `src/components/layout/AppContent.vue` 调整内容渲染
