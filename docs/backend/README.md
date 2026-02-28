# 后端架构文档

## 文档体系

系统架构文档采用**分层文档架构**，理念与实施分离：

### 核心文档

| 文档 | 类型 | 内容范围 |
|------|------|----------|
| **DATABASE_COORDINATED_ARCHITECTURE.md** | 核心理念 | 架构哲学、设计原则、抽象模型 |
| **QUANT_TRADING_SYSTEM_ARCHITECTURE.md** | 详细实施 | 数据库设计、表结构、触发器、流程图 |

### 补充文档

| 文档 | 说明 |
|------|------|
| `tradingview-api.md` | TradingView 数据源 API 规范 |
| `database/kline-optimization.md` | K线表优化设计 |

## 目录结构

```
docs/
├── backend/                    # 后端架构设计
│   ├── design/                 # 核心设计文档
│   │   ├── DATABASE_COORDINATED_ARCHITECTURE.md
│   │   ├── QUANT_TRADING_SYSTEM_ARCHITECTURE.md
│   │   └── tradingview-api.md
│   ├── database/               # 数据库设计
│   │   └── kline-optimization.md
│   └── events/                 # 事件定义
├── codemaps/                   # 代码地图
└── testing/                    # 测试文档
```

## 阅读指南

### 新开发人员
1. **先读** `DATABASE_COORDINATED_ARCHITECTURE.md` - 理解系统设计思想
2. **再读** `QUANT_TRADING_SYSTEM_ARCHITECTURE.md` - 掌握实施细节

### 资深开发人员
- 快速查阅 `QUANT_TRADING_SYSTEM_ARCHITECTURE.md` 获取实施细节
- 查阅 `DATABASE_COORDINATED_ARCHITECTURE.md` 了解设计理念

---

**版本**：v3.0
**更新**：2026-02-21
