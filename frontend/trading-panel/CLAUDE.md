# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码仓库中工作提供指导。

## 常用开发命令

### 依赖安装
> **重要**：由于网络原因，请使用 `cnpm install` 而非 `npm install`，以避免无法访问 npm 镜像的问题。

```bash
# 安装依赖（使用淘宝镜像）
cnpm install

# 安装新依赖
cnpm add <package-name>

# 开发、构建命令
npm run dev      # 启动开发服务器
npm run build    # 生产构建
npm run preview  # 预览构建产物
```

### 核心脚本
- **`npm run dev`** - 启动开发服务器，支持热模块替换。运行在 http://127.0.0.1:5173。支持 Vue 前端和 Electron 渲染进程的同步开发。
- **`npm run build`** - 完整生产构建。运行 TypeScript 类型检查，构建 Vue/Vite 前端和 Electron 主进程，然后使用 electron-builder 打包。
- **`npm run preview`** - 在本地服务生产构建版本，用于分发前测试。

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

## 高层架构

这是一个用于量化交易的 **Electron + Vue 3 + Vite** 桌面应用，具有多标签页系统和 TradingView 图表集成。

### 进程架构

**主进程** (`electron/main/index.ts`)
- 创建和管理应用程序窗口
- 处理应用程序生命周期事件
- 安全配置：`nodeIntegration: false`, `contextIsolation: true`
- 开发模式：自动打开 DevTools

**预加载脚本** (`electron/preload/index.ts`)
- 通过 `contextBridge` 安全桥接主进程和渲染进程
- 暴露 API：Tabs（标签管理）、Window（窗口控制）、App（应用信息）
- 所有 IPC 通信都通过此层进行

**渲染进程** (Vue 3 应用)
- 现代化的 Vue 3 组合式 API
- Pinia 状态管理
- Naive UI 组件库，支持暗色主题
- 多标签页界面，采用单例模式（每个模块类型仅一个实例）

### 核心组件

```
src/
├── components/
│   ├── layout/           # 应用布局（Header, Content, Footer）
│   └── TradingViewChart/ # 金融图表组件
├── stores/
│   └── tab-store.ts      # Pinia 标签页管理存储
├── views/
│   ├── ModuleA.vue       # TradingView K线图
│   ├── ModuleB.vue       # 测试模块
│   └── ModuleC.vue       # 测试模块
└── App.vue               # 带有标签系统的根组件
```

### TradingView 集成
- **组件**：`src/components/TradingViewChart/index.vue`
- **Hook**：`composables/useTradingView.js` - 管理组件生命周期
- **库**：本地 TradingView 图表库位于 `library/`
- **默认交易对**：BINANCE:BTCUSDT，1小时周期
- **技术指标**：5EMA、MACD（自动加载）

## 技术决策（来自项目文档）

### Vue vs WebContentsView 架构
项目使用 **基于 Vue 的多标签页架构** 而非 WebContentsView，原因如下：

**选择 Vue 的原因：**
- 实现和维护更简单
- 更好地集成 Vue 生态系统（Pinia、Naive UI）
- 统一的样式和主题
- 跨标签页状态管理更简单
- 标签页切换性能更好（v-show vs 创建/销毁 WebContents）

**架构设计：**
- 单个 Vue 应用，动态组件渲染
- 标签页状态由 Pinia 存储管理
- 基于活动标签挂载/卸载组件
- 单例模式：每种模块类型只能有一个标签页

详见 `docs/tech-decision-vue-vs-webcontentsview.md` 中的完整对比。

### BrowserView 优化策略
为处理复杂 UI 场景（弹窗层、对话框、热键），项目实现了 `docs/browserview_electron_optimization.md` 中记录的策略：

**关键方法：**
- 对标签页内容使用 v-show 而非 v-if（保持状态）
- 在应用层级管理弹窗层，而非 BrowserView 内
- 实现正确的事件清理以防止内存泄漏
- 优化进程间数据通信

## 项目结构

### 核心目录
- **`electron/`** - 主进程和预加载脚本
  - `main/index.ts` - 窗口创建和生命周期管理
  - `preload/index.ts` - 安全 IPC 桥接
- **`src/`** - Vue 渲染进程
  - `components/` - 可复用 Vue 组件
  - `stores/` - Pinia 状态管理
  - `views/` - 模块/页面组件
  - `assets/` - 静态资源
- **`public/`** - 公共静态资源
- **`docs/`** - 技术文档（中文）
- **`release/`** - 构建安装包输出

### 配置文件
- **`vite.config.ts`** - Vite 构建配置，集成 Electron
- **`electron-builder.json5`** - Windows/macOS/Linux 打包配置
- **`tsconfig.json`** - Vue/TypeScript 配置

## 开发说明

### 热重载行为
- **渲染进程**：修改自动刷新页面
- **预加载脚本**：修改自动重载页面（无需重启应用）
- **主进程**：修改需要重启应用

### 安全模型
- 启用上下文隔离
- 在渲染进程中禁用 Node.js 集成
- 所有外部 API 通过预加载脚本暴露
- 在渲染进程中通过 `window.api` 访问允许的操作

### 状态管理模式
- 标签页存储 (`stores/tab-store.ts`) 管理所有标签页操作
- 强制执行单例模式：不能创建重复的模块标签页
- 必须保持至少一个标签页打开
- 标签页配置由数据驱动（标题、颜色、组件）

### 构建配置
- ES 模块（`package.json` 中的 `"type": "module"`）
- 双构建输出：前端 (`dist/`) + Electron (`dist-electron/`)
- 外部化 Node.js 依赖以避免打包问题
- 生产构建启用 ASAR 压缩

## 关键修改文件

### 添加新模块
1. 在 `src/views/NewModule.vue` 中创建组件
2. 在 `src/stores/tab-store.ts` 中添加模块配置
3. 在标签页存储中导入并注册

### 修改标签页行为
- 编辑 `src/stores/tab-store.ts` 调整标签页管理逻辑
- 更新 `src/components/layout/AppHeader.vue` 调整标签页 UI
- 修改 `src/components/layout/AppContent.vue` 调整内容渲染

### TradingView 自定义
- 编辑 `src/components/TradingViewChart/composables/useTradingView.js` 调整组件选项
- 在组合式函数中修改默认交易对/周期
- 在初始化代码中调整技术指标

### TradingView Datafeed API 重要经验教训

**getQuotes vs subscribeQuotes 数据格式差异**

在实现 TradingView watchlist 功能时发现，getQuotes 和 subscribeQuotes 方法返回的数据格式不一致：

- **getQuotes**: 返回数组格式 `[quote1, quote2, ...]`
- **subscribeQuotes**: 返回单个对象格式 `quote`

**问题表现**：
- watchlist 能显示初始数据（来自 getQuotes）
- watchlist 无法实时更新（subscribeQuotes 数据格式不匹配）

**解决方案**：
在 `src/components/TradingViewChart/utils/datafeed.js` 第326行，将 subscribeQuotes 的 payload 包装成数组：

```javascript
// 修复: 将payload包装成数组格式，以匹配getQuotes的数据格式
const quoteDataArray = [payload];
subscription.onRealtimeCallback(quoteDataArray);
```

**调试方法**：
使用 `test-getquotes.js` 和 `test-watchlist-debug.js` 验证数据格式差异，确保 watchlist 能正确处理两种数据源。

### Electron API 变更
- 在 `electron/preload/index.ts` 中添加新 API
- 在 `electron/main/index.ts` 中实现处理程序
- 通过 `window.api` 在渲染进程中访问

## 依赖概览

### 生产依赖
- **Vue 3.5.21** - UI 框架
- **Pinia 3.0.4** - 状态管理
- **Naive UI 2.43.2** - UI 组件库
- **@vicons/ionicons5** - 图标库
- **Electron 39.2.1** - 桌面框架

### 开发依赖
- **Vite 7.3.0** - 构建工具
- **TypeScript 5.9.3** - 类型检查
- **electron-builder 26.0.0** - 打包工具

## 故障排除

### 构建失败，TypeScript 报错
- 运行 `vue-tsc --noEmit` 检查类型
- 构建前修复类型错误

### 热重载不工作
- 确保 `npm run dev` 正在运行
- 检查控制台错误
- 如果修改了预加载脚本，请重启

### TradingView 图表无法加载
- 验证 `src/components/TradingViewChart/library/` 存在
- 检查浏览器控制台的组件错误
- 确保交易对格式正确（例如，BINANCE:BTCUSDT）

### Watchlist 数据不更新
- 检查 `src/components/TradingViewChart/utils/datafeed.js` 中的 getQuotes 和 subscribeQuotes 数据格式
- 确认 subscribeQuotes 的 payload 被正确包装成数组格式
- 使用 `test-watchlist-debug.js` 验证数据格式差异
- 监控浏览器控制台中的 WebSocket 消息和回调函数调用
