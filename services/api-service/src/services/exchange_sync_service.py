"""
交易所信息同步服务

此服务已停用，交易所信息同步功能已迁移到 binance-service。

历史功能（已迁移到 binance-service）：
- 定时从币安API获取交易所信息
- 更新 exchange_info 表
- 运行周期：每30分钟

binance-service 负责：
- 获取现货/期货交易所信息
- 写入 exchange_info 表
"""
