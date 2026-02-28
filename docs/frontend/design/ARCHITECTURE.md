# 前端架构设计

本文档描述量化交易系统前端的架构设计和技术决策。

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Electron | 39.2.7 | 桌面应用框架 |
| Vue | 3.5.21 | UI 框架 |
| Vite | 7.3.0 | 构建工具 |
| TypeScript | 5.9.3 | 类型检查 |
| Pinia | 3.0.4 | 状态管理 |
| Naive UI | 2.43.2 | UI 组件库 |
| electron-builder | 26.0.0 | 打包工具 |

## 进程架构

前端采用 Electron 多进程架构，分为三个部分：

### 主进程

**文件**: `electron/main/index.ts`

- 创建和管理应用程序窗口
- 处理应用程序生命周期事件
- 安全配置: `nodeIntegration: false`, `contextIsolation: true`
- 开发模式自动打开 DevTools

### 预加载脚本

**文件**: `electron/preload/index.ts`

- 通过 `contextBridge` 安全桥接主进程和渲染进程
- 暴露 API (通过 `window` 对象访问):
  - `window.tabs`: 标签管理
  - `window.window`: 窗口控制
  - `window.app`: 应用信息
- 所有 IPC 通信都通过此层进行

### 渲染进程

**技术**: Vue 3 组合式 API

- Pinia 状态管理
- Naive UI 组件库，支持暗色主题
- 多标签页界面，采用单例模式（每个模块类型仅一个实例）

## 核心组件结构

```
src/
├── components/
│   ├── layout/           # 应用布局
│   │   ├── AppHeader.vue # 顶部导航和标签栏
│   │   └── AppContent.vue # 主体内容区域
│   └── TradingViewChart/ # TradingView 图表组件
│       ├── index.vue     # 图表主组件
│       ├── composables/  # 组合式函数
│       │   └── useTradingView.js
│       ├── utils/        # 工具函数
│       │   └── datafeed.js
│       └── library/     # TradingView 库文件
├── stores/
│   ├── tab-store.ts      # 标签页状态管理
│   └── account-store.ts  # 账户状态管理
├── views/
│   ├── ModuleA.vue      # TradingView K线图模块
│   ├── ModuleB.vue      # 测试模块
│   ├── ModuleC.vue      # 测试模块
│   └── AccountDashboard.vue # 账户仪表盘
├── types/               # TypeScript 类型定义
├── composables/         # 可复用组合式函数
├── theme/              # 主题配置
└── App.vue             # 根组件
```

## 目录说明

### electron/

| 目录 | 说明 |
|------|------|
| `main/index.ts` | Electron 主进程入口，负责窗口创建和生命周期管理 |
| `preload/index.ts` | 预加载脚本，安全暴露 API 给渲染进程 |

### src/components/

| 目录/文件 | 说明 |
|-----------|------|
| `layout/AppHeader.vue` | 应用头部，包含标签页导航 |
| `layout/AppContent.vue` | 内容区域，渲染活动标签页 |
| `TradingViewChart/` | TradingView 图表集成组件 |

### src/stores/

| 文件 | 说明 |
|------|------|
| `tab-store.ts` | 标签页状态管理，维护所有标签页操作 |
| `account-store.ts` | 账户状态管理，维护账户信息 |

### src/views/

| 文件 | 说明 |
|------|------|
| `ModuleA.vue` | TradingView K线图模块 |
| `ModuleB.vue` | 测试模块 B |
| `ModuleC.vue` | 测试模块 C |
| `AccountDashboard.vue` | 账户仪表盘 |

## 架构决策

### Vue vs WebContentsView

项目使用**基于 Vue 的多标签页架构**而非 WebContentsView，原因如下：

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

### 状态管理模式

- 标签页存储 (`stores/tab-store.ts`) 管理所有标签页操作
- 强制执行单例模式：不能创建重复的模块标签页
- 必须保持至少一个标签页打开
- 标签页配置由数据驱动（标题、颜色、组件）

## 安全模型

- 启用上下文隔离 (`contextIsolation: true`)
- 在渲染进程中禁用 Node.js 集成 (`nodeIntegration: false`)
- 所有外部 API 通过预加载脚本暴露
- 在渲染进程中通过 `window.api` 访问允许的操作

## 构建配置

- ES 模块（`package.json` 中的 `"type": module"`）
- 双构建输出：前端 (`dist/`) + Electron (`dist-electron/`)
- 外部化 Node.js 依赖以避免打包问题
- 生产构建启用 ASAR 压缩

## 构建输出

| 目录 | 说明 |
|------|------|
| `dist/` | Vue 应用构建产物 |
| `dist-electron/main/` | Electron 主进程 |
| `dist-electron/preload/` | 预加载脚本 |
| `release/` | 平台特定安装包 |

## 相关文档

- [前端 CLAUDE.md](../../frontend/trading-panel/CLAUDE.md) - 开发命令和详细说明
- [技术决策：Vue vs WebContentsView](../../frontend/trading-panel/docs/tech-decision-vue-vs-webcontentsview.md)
- [BrowserView 优化策略](../../frontend/trading-panel/docs/browserview_electron_optimization.md)
