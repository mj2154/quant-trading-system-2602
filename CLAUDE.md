# 事件驱动量化交易系统

> **个人用量化交易系统 - 避免过度设计**
>
> 这是一个**个人开发环境**的量化交易系统，非生产环境。
> - 不需要高可用、集群、复制
> - 不需要复杂的性能调优
> - 不需要企业级安全配置
> - 优先使用默认配置，仅在必要时才自定义
> - Docker 部署：直接用官方镜像，不要自定义复杂配置

基于TimescaleDB和PostgreSQL通知机制的微服务量化交易系统。采用**数据库协调的事件驱动架构**，通过数据库作为调度中心实现服务间松耦合通信，支持实时K线采集、信号计算、回测和自动交易。

**核心理念**: 数据库即调度中心，事件驱动架构，状态集中管理，服务松耦合。

## 核心文档

**系统采用分层文档架构**，理念与实施分离：

### 📖 核心理念文档

**《基于数据库协调的轻量级任务调度架构》** 位于 `docs/backend/design/DATABASE_COORDINATED_ARCHITECTURE.md`

该文档是系统的**核心理念与设计哲学指南**，详细阐述了：
- 数据库即调度中心的架构思想
- 四大设计原则（职责单一、数据库中心化、松耦合、事件驱动）
- 事件驱动架构设计理念
- 适用场景和决策标准

**所有架构决策和设计理念都必须参考此文档**，确保与核心思想保持一致。

### 🛠️ 详细实施文档

**《量化交易系统架构设计》** 位于 `docs/backend/design/QUANT_TRADING_SYSTEM_ARCHITECTURE.md`

该文档是系统的**详细实施指南**，包含：
- 完整的数据库表结构和设计
- 所有触发器和存储过程实现
- 任务调度和订阅管理机制
- 数据流设计和事件链实现
- 交易所信息全量替换策略

**所有开发和实现都必须严格遵循此文档**，确保实施细节准确。

### 📚 文档体系索引

**《架构文档体系指南》** 位于 `docs/backend/README.md`

该文档提供了完整的文档导航和阅读指南：
- 文档体系介绍和阅读建议
- 核心理念文档与实施文档的关系
- 不同读者群体的阅读路径
- 文档维护和同步机制

### 📖 相关设计文档

**《量化交易系统架构设计》** (`docs/backend/design/QUANT_TRADING_SYSTEM_ARCHITECTURE.md`) 包含：
- 数据库协同架构详细设计
- 任务调度和订阅管理机制
- WebSocket API协议格式
- REST API请求/响应结构
- 完整的数据流设计

### 第三方API参考文档

币安官方API文档位于以下目录，实现数据采集和交易功能时必须参考：

- **U本位合约API**: `/home/ppadmin/code/binance-docs/binance_futures_docs/`
- **现货API**: `/home/ppadmin/code/binance-docs/binance_spot_docs/`

## 核心架构

- **数据库中心**: TimescaleDB作为唯一数据源和调度中心，所有任务通过数据库协调
- **事件驱动**: PostgreSQL NOTIFY/LISTEN实现服务间通信，服务间不直接通信
- **松耦合架构**: 服务独立部署，通过数据库事件协调，无共享状态
- **实时推送**: API服务通过WebSocket向前端推送数据变化
- **状态集中**: 所有系统状态持久化在数据库，无内存状态，重启无影响

## 技术栈

- **数据库**: TimescaleDB (PostgreSQL扩展) - Docker容器运行
- **后端**: Python 3.14+ (FastAPI/AsyncIO)
- **容器**: Docker + Docker Compose
- **包管理**: uv (Python包管理)
- **API网关**: Clash Proxy (网络代理)

## 设计原则：避免过度设计

### 个人开发环境原则

**禁止过度设计的配置**:
- Docker: 直接用官方镜像，不要自定义复杂配置
- PostgreSQL: 使用默认配置，不要调优参数
- TimescaleDB: 使用默认配置，不需要调优
- 日志: 使用容器日志驱动，不要复杂的日志配置
- 网络: 使用默认 bridge 网络，不要自定义子网

**正确做法**:
- 能用默认配置就用默认配置
- 官方镜像已针对大多数场景优化
- 先让系统跑起来，有问题再优化

**错误做法**:
- 为个人开发环境配置复制、高可用
- 花大量时间调优数据库参数
- 自定义复杂的 postgresql.conf
- 配置企业级安全策略

## Critical Rules

### 1. 微服务架构规范

- **服务独立**: 每个服务独立目录、独立部署、独立依赖
- **松耦合**: 服务间通过PostgreSQL通知通信，避免直接API调用
- **数据库中心**: 所有数据写入TimescaleDB，通过触发器触发事件
- **事件驱动**: 遵循`写入→触发→通知→订阅`的事件链模式
### 2. 代码组织原则

- 多个小文件优于一个大文件
- 高内聚，低耦合
- 每文件200-400行，最多800行
- 按功能/域组织，而非按类型组织
- 每服务独立`src/`、`tests/`、`docs/`目录

### 3. 事件驱动模式

- **K线事件链**: 采集→写入→kline.new事件→信号计算
- **信号事件链**: 信号写入→signal.new事件→交易决策
- **交易事件链**: 交易执行→trade.completed事件→账户更新
- **通知频道**: 使用PostgreSQL NOTIFY/LISTEN机制
- **事件数据**: JSON格式，包含event_id、event_type、timestamp、data

### 4. 代码风格

- 代码、注释、文档中禁止使用emoji
- 优先使用不可变数据，避免修改对象或数组
- 生产代码禁止使用print()，使用结构化日志
- 完善的错误处理，使用try/catch包装关键逻辑
- 使用Pydantic进行输入验证和类型检查
- 使用async/await进行异步编程
- Python类型注解是必须的

### 5. 日志规范

- 所有服务使用结构化JSON日志
- 日志级别: DEBUG < INFO < WARNING < ERROR < CRITICAL
- 关键业务事件必须记录（交易、信号、账户变化）
- 错误日志包含traceback和上下文信息
- 使用统一的日志格式: `timestamp - service - level - message - metadata`

### 6. 测试规范

- **TDD优先**: 先写测试，再写实现代码
- **覆盖率**: 核心业务逻辑必须达到80%+覆盖率
- **单元测试**: 工具函数、算法逻辑使用pytest
- **集成测试**: API接口、数据库操作、事件处理
- **E2E测试**: 关键业务流程（K线→信号→交易）
- **测试隔离**: 每个服务独立测试，使用测试数据库

### 7. 安全性

- 严禁硬编码密钥，使用环境变量管理敏感信息
- API密钥、数据库密码等存储在`.env`文件
- 验证所有用户输入，包括API参数和WebSocket消息
- 仅使用参数化查询，防止SQL注入
- 交易API必须实现速率限制和授权验证
- 生产环境启用HTTPS和WSS（WebSocket Secure）

### 8. 数据库初始化规范

**单一真相来源**: 所有数据库初始化脚本统一放在 `docker/init-scripts/01-database-init.sql`

- 表结构、触发器、函数等必须在该文件中定义
- 数据库重构后，执行该脚本即可恢复所有功能
- **禁止**在其他位置放置SQL文件（migrations目录仅用于版本追溯）
- 不要在多个服务目录下分散放置SQL脚本

## 目录结构

```
quant-trading/
├── services/                    # 后端微服务
│   ├── api-service/           # API服务 (端口8000)
│   │   └── src/
│   │       ├── main.py        # FastAPI入口
│   │       ├── gateway/       # WebSocket网关
│   │       │   ├── websocket_handler.py  # WebSocket处理
│   │       │   ├── client_manager.py    # 客户端管理
│   │       │   ├── subscription_manager.py  # 订阅管理
│   │       │   └── realtime_handler.py     # 实时数据处理
│   │       ├── db/            # 数据库仓储
│   │       │   ├── database.py       # 数据库连接
│   │       │   ├── tasks_repository.py
│   │       │   ├── subscription_repository.py
│   │       │   └── realtime_data_repository.py
│   │       ├── models/        # 数据模型
│   │       ├── converters/    # 数据转换器
│   │       ├── services/      # 业务服务
│   │       └── protocol/      # 协议定义
│   ├── binance-service/       # 币安API服务 (端口8001)
│   │   ├── src/
│   │   │   ├── collectors/   # 数据采集器
│   │   │   ├── storage/       # 数据存储
│   │   │   └── events/        # 事件发布
│   │   └── main.py
│   ├── signal-service/        # 信号计算服务 (新)
│   │   ├── src/
│   │   │   ├── main.py        # 服务入口
│   │   │   ├── db/            # 数据库仓储
│   │   │   │   ├── database.py       # 数据库连接
│   │   │   │   ├── realtime_data_repository.py
│   │   │   │   └── strategy_signals_repository.py
│   │   │   ├── listener/      # 通知监听
│   │   │   │   └── realtime_update_listener.py
│   │   │   ├── strategies/    # 策略计算
│   │   │   │   ├── base.py    # 策略抽象基类
│   │   │   │   └── random_strategy.py  # 随机策略（测试用）
│   │   │   └── services/      # 业务服务
│   │   │       └── signal_service.py
│   │   ├── tests/
│   │   └── pyproject.toml
│   ├── trading/              # 交易系统 (端口8003)
│   │   ├── src/
│   │   │   ├── engine/       # 交易引擎
│   │   │   ├── risk/         # 风险管理
│   │   │   ├── account/      # 账户管理
│   │   │   └── events/       # 事件监听
│   │   └── main.py
│   └── clash-proxy/          # 网络代理 (端口7890-7892,9090)
│
├── shared/                    # 共享代码
│   ├── python/              # Python共享模块
│   │   ├── converters/      # 币安数据转换器
│   │   │   └── binance/    # 币安API转换器
│   │   ├── models/         # 共享数据模型
│   │   ├── constants/      # 常量定义
│   │   └── utils/          # 工具函数
│   ├── typescript/          # TypeScript类型定义
│   └── schemas/             # 数据模式
│
├── docker/                   # Docker配置
│   ├── docker-compose.yml
│   └── init-scripts/
│       ├── 01-database-init.sql           # 数据库初始化 (单一真相来源)
│       ├── 02-migrate-to-unified-architecture.sql  # 架构迁移
│       ├── 03-migrate-klines-history.sql   # K线历史迁移
│       ├── 99-verify-migration.sql        # 迁移验证
│       └── 99-verify-final.sql             # 最终验证
│
├── docs/                     # 项目文档
│   ├── api/                 # API文档
│   ├── architecture/         # 架构设计
│   │   ├── README.md                # 文档体系指南
│   │   ├── DATABASE_COORDINATED_ARCHITECTURE.md  # 核心理念文档
│   │   ├── QUANT_TRADING_SYSTEM_ARCHITECTURE.md  # 详细实施文档
│   │   └── TradingView-完整API规范设计文档.md
│   ├── database/            # 数据库相关
│   ├── archive/             # 归档文档
│   ├── deployment/         # 部署文档
│   ├── development/        # 开发文档
│   └── troubleshooting/    # 故障排除
│
├── frontend/                 # 前端应用
├── configs/                  # 配置文件
├── scripts/                  # 运维脚本
├── tests/                    # 全局测试
└── backups/                 # 备份文件
```

### 重要提醒

**数据库协调架构的核心原则**：

1. **数据库即调度中心** (`docs/backend/design/DATABASE_COORDINATED_ARCHITECTURE.md`) 是项目的**设计哲学指南**，所有任务调度通过数据库实现：
   - 数据库即调度中心，服务间不直接通信
   - 四大设计原则：职责单一、数据库中心化、松耦合、事件驱动
   - 状态集中化：所有系统状态持久化在数据库
   - 事件驱动：数据库变化自动触发通知，消费者被动响应

2. **详细实施文档** (`docs/backend/design/QUANT_TRADING_SYSTEM_ARCHITECTURE.md`) 是项目的**实施权威**，包含：
   - 完整的系统架构图和数据流设计
   - 数据库表结构、触发器和存储过程
   - 微服务交互模式和任务调度机制
   - 订阅管理和实时数据推送实现

**任何架构决策必须参考核心理念文档，任何实现方案必须参考实施文档**，确保设计思想与实施细节保持一致。

## 配置管理

### 环境变量原则

- **敏感信息**: API密钥、数据库密码等敏感信息必须通过环境变量管理
- **配置文件**: 不同环境（开发/测试/生产）使用独立配置文件
- **变量命名**: 使用统一的前缀和命名规范
- **文档化**: 记录所有必要的环境变量及其用途

### 配置分离

- 业务配置与代码分离
- 环境特定配置通过环境变量或独立文件管理
- 使用配置管理工具（如pydantic-settings）加载配置
- 避免在代码中硬编码配置值

## 项目管理规范

### Python包管理

- **统一使用uv**: 每个服务独立使用uv进行包管理和依赖管理
- **依赖添加**: 进入服务目录后使用`uv add package-name`添加依赖
- **禁止方式**:
  - 禁止在根目录编写pyproject.toml（各服务独立管理）
  - 禁止手动编写requirements.txt，pyproject.toml文件
  - 禁止使用`uv pip install`和`pip install`命令安装依赖
- **脚本运行**: 在服务目录内使用`uv run python script.py`，禁止直接使用`python`

### 依赖管理原则

- **独立管理**: 每个服务独立管理依赖，拥有独立的pyproject.toml文件
- **无workspace**: 不使用uv workspace，确保服务间完全隔离
- **依赖隔离**: 每个服务有自己的.venv环境，避免依赖冲突
- 共享代码放置在`shared/`目录（不包含uv依赖）
- 生产环境固定版本，开发环境可使用版本范围
- 定期更新依赖，但需经过充分测试验证

### 微服务脚本运行

由于每个微服务都独立管理自己的依赖（拥有独立的pyproject.toml文件），运行任何微服务的脚本时必须先进入该服务的目录：

- **API服务**: `cd services/api-service && uv run python src/main.py`
- **币安服务**: `cd services/binance-service && uv run python main.py`
- **信号服务**: `cd services/signal-service && uv run python main.py`
- **交易系统**: `cd services/trading && uv run python main.py`

每个服务的脚本都必须在各自的服务目录下运行，这样才能正确加载该服务的依赖和环境配置。

### Docker容器操作

- **启动所有服务**: `cd docker && docker-compose up -d`
- **查看日志**: `cd docker && docker-compose logs -f [service-name]`
- **停止所有服务**: `cd docker && docker-compose down`
- **重启服务**: `cd docker && docker-compose restart [service-name]`
- **进入容器**: `docker exec -it [container-name] /bin/bash`

所有Docker相关文件位于`docker/`目录下，包括docker-compose.yml和Docker配置文件。

### 数据库调试

**数据库运行在Docker容器中**，调试必须进入容器执行命令：

```bash
# 进入TimescaleDB容器
docker exec -it timescale-db /bin/bash

# 在容器内连接数据库
psql -U dbuser -d trading_db

# 执行SQL文件
psql -U dbuser -d trading_db -f /tmp/migrate.sql

# 复制文件到容器
docker cp local-file.sql timescale-db:/tmp/file.sql
```

**常用连接信息**:
- 主机: `timescale-db` (容器名)
- 数据库: `trading_db`
- 用户: `dbuser`
- 密码: `pass`
- 端口: `5432`

## 开发流程

### 标准工作流

- **TDD优先**: 先编写测试，再实现功能
- **分支策略**: 使用功能分支（feature/xxx）进行开发
- **代码审查**: 所有PR必须经过至少1人审查
- **测试要求**: 所有测试通过才能合并代码
- **持续集成**: 每次提交自动运行测试套件

### 提交规范

使用约定式提交格式：
- `feat:` - 新功能开发
- `fix:` - 错误修复
- `refactor:` - 代码重构
- `docs:` - 文档更新
- `test:` - 测试相关
- `chore:` - 构建/工具/辅助功能

### 分支管理

- **主分支**: main分支受保护，禁止直接推送
- **开发分支**: feature分支从main切出
- **修复分支**: hotfix分支用于紧急修复
- **合并策略**: 使用PR进行代码审查后合并

## 质量保证

### 代码审查要点

- 代码是否符合项目规范
- 测试覆盖率是否达标（核心逻辑80%+）
- 日志记录是否完整
- 错误处理是否完善
- 性能影响评估
- 安全性检查

### 测试策略

- **单元测试**: 测试工具函数和算法逻辑
- **集成测试**: 测试API接口和数据库交互
- **E2E测试**: 测试完整业务流程
- **测试隔离**: 每个服务独立测试环境

## 注意事项

### 架构原则

- **事件驱动**: 遵循写入→触发→通知→订阅模式
- **数据中心**: TimescaleDB作为唯一数据源
- **服务独立**: 微服务间通过事件通信，避免直接API调用
- **松耦合**: 服务间无直接依赖

### 开发规范

- **代码风格**: 使用ruff进行代码格式化和错误检测
- **类型注解**: Python代码必须包含类型注解
- **文档字符串**: 重要函数和类必须编写docstring
- **日志规范**: 使用结构化日志，记录关键业务事件

### 性能考虑

- 数据库查询优化，避免N+1查询
- 合理配置连接池大小
- 异步处理非阻塞操作
- 监控关键性能指标

### 安全要求

- 严禁硬编码敏感信息
- 所有输入必须验证
- 使用参数化查询防止SQL注入
- 交易API实现速率限制
- 定期更新安全依赖包

## 文档阅读指南

### 新团队成员

1. **第一步**：阅读 `docs/backend/README.md` 了解文档体系
2. **第二步**：阅读 `docs/backend/design/DATABASE_COORDINATED_ARCHITECTURE.md` 理解设计理念
3. **第三步**：阅读 `docs/backend/design/QUANT_TRADING_SYSTEM_ARCHITECTURE.md` 掌握实施细节

### 开发人员

- **日常开发**：主要查阅 `QUANT_TRADING_SYSTEM_ARCHITECTURE.md` 获取实施细节
- **遇到问题**：参考 `DATABASE_COORDINATED_ARCHITECTURE.md` 理解设计意图
- **代码变更**：更新相应文档章节

### 架构师

- **定期回顾**：每季度回顾核心理念文档
- **新功能设计**：优先在理念文档中阐述设计思想
- **文档维护**：确保两个文档的一致性