# 前端开发指南

## 开发环境

### 依赖安装

> **重要**: 由于网络原因，请使用 `cnpm install` 而非 `npm install`，以避免无法访问 npm 镜像的问题。

```bash
# 进入前端目录
cd frontend/trading-panel

# 安装依赖（使用淘宝镜像）
cnpm install

# 安装新依赖
cnpm add <package-name>
```

### 核心命令

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动开发服务器，支持热模块替换。运行在 http://127.0.0.1:5173 |
| `npm run build` | 完整生产构建，运行 TypeScript 类型检查，构建 Vue/Vite 前端和 Electron 主进程 |
| `npm run preview` | 在本地服务生产构建版本，用于分发前测试 |

### 构建流程

构建命令包含三个阶段：
1. TypeScript 类型检查 (`vue-tsc --noEmit`)
2. Vite 生产构建
3. Electron 打包为可分发文件

输出目录：
- `dist/` - Vue 应用构建产物
- `dist-electron/main/` - Electron 主进程
- `dist-electron/preload/` - 预加载脚本
- `release/` - 平台特定安装包

## 热重载行为

| 进程 | 热重载行为 |
|------|------------|
| 渲染进程 | 修改自动刷新页面 |
| 预加载脚本 | 修改自动重载页面（无需重启应用） |
| 主进程 | 修改需要重启应用 |

## 故障排除

### 构建失败，TypeScript 报错

```bash
vue-tsc --noEmit
```

- 运行 `vue-tsc --noEmit` 检查类型
- 构建前修复类型错误

### 热重载不工作

- 确保 `npm run dev` 正在运行
- 检查控制台错误
- 如果修改了预加载脚本，请重启应用

### TradingView 图表无法加载

- 验证 `src/components/TradingViewChart/library/` 存在
- 检查浏览器控制台的组件错误
- 确保交易对格式正确（例如，BINANCE:BTCUSDT）

### Watchlist 数据不更新

- 检查 `src/components/TradingViewChart/utils/datafeed.js` 中的 getQuotes 和 subscribeQuotes 数据格式
- 确认 subscribeQuotes 的 payload 被正确包装成数组格式
- 使用测试脚本验证数据格式差异
- 监控浏览器控制台中的 WebSocket 消息和回调函数调用
