# 状态管理

## Pinia 存储

前端使用 Pinia 进行状态管理。

### 标签页存储

**文件**: `src/stores/tab-store.ts`

管理所有标签页操作：

- 创建标签页
- 关闭标签页
- 切换活动标签页
- 强制执行单例模式

### 账户存储

**文件**: `src/stores/account-store.ts`

管理账户信息：

- 账户余额
- 持仓信息
- 交易历史

## 状态管理原则

### 单例模式

- 标签页存储管理所有标签页操作
- 强制执行单例模式：不能创建重复的模块标签页
- 必须保持至少一个标签页打开
- 标签页配置由数据驱动（标题、颜色、组件）

### 数据驱动

标签页配置由数据驱动，存储结构示例：

```typescript
interface Tab {
  id: string
  title: string
  color: string
  component: string
}
```
