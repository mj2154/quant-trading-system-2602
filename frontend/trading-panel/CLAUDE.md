# Trading Panel (Frontend)

量化交易系统 Electron 桌面前端，基于 Vue 3 + Vite + Pinia。

## Commands

| Command | Description |
|---------|-------------|
| `pnpm install` | 安装依赖 |
| `pnpm dev` | 启动开发服务器 (http://localhost:5173) |
| `pnpm build` | 生产构建 + Electron 打包 |
| `pnpm preview` | 预览构建产物 |
| `pnpm lint` | 代码检查 (ESLint) |
| `pnpm test` | 运行单元测试 |

## Architecture

```
frontend/trading-panel/
├── electron/           # Electron 主进程
│   ├── main/          # 主进程入口
│   └── preload/       # 预加载脚本
├── src/
│   ├── components/    # Vue 组件
│   │   ├── TradingViewChart/  # TradingView 图表
│   │   ├── alert/    # 告警管理组件
│   │   ├── signal/   # 信号展示组件
│   │   └── layout/   # 布局组件
│   ├── composables/  # 组合式函数
│   ├── libs/         # 工具库
│   │   └── ws-client/  # WebSocket 客户端
│   ├── services/     # 数据服务层
│   ├── stores/       # Pinia 状态管理
│   │   ├── alert-store.ts    # 告警状态
│   │   ├── strategy-store.ts # 策略状态
│   │   ├── trading-store.ts  # 交易状态
│   │   ├── account-store.ts  # 账户状态
│   │   └── tab-store.ts      # 标签页管理
│   ├── types/        # TypeScript 类型定义
│   └── views/        # 页面组件
│       ├── TradingDashboard.vue
│       ├── AlertDashboard.vue
│       └── AccountDashboard.vue
├── public/           # 静态资源
├── vite.config.ts    # Vite + Electron 配置
└── electron-builder.json5  # 打包配置
```

## Key Files

- `src/services/data-service/DataService.ts` - 统一数据接口
- `src/libs/ws-client/WSClient.ts` - WebSocket 客户端
- `src/components/TradingViewChart/utils/datafeed.js` - TradingView DataFeed
- `src/stores/tab-store.ts` - 标签页系统（动态组件，非 Vue Router）

## Environment

- 后端 API: `http://localhost:8000` (通过 vite 代理)
- WebSocket: `ws://localhost:8000/ws`

## Gotchas

- **包管理器**:
  - 普通依赖: 使用 `pnpm`
  - Electron 相关: **必须使用 `cnpm`**（npm/pnpm 安装 electron 会遇到网络问题）
- **标签页系统**: 使用动态组件 + Pinia 实现，非 Vue Router
- **TradingView DataFeed**: `subscribeQuotes` 返回单个对象，`getQuotes` 返回数组，需转换格式
- **Electron 开发**: 修改主进程需重启应用，修改渲染进程自动热重载
- **WS客户端**: 消息类型需严格按 `libs/ws-client/types.ts` 定义，禁止随意添加字典
