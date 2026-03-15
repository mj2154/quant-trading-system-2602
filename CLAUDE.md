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

## 快速开始

| Command | Description |
|---------|-------------|
| `cd docker && docker-compose up -d` | 启动所有服务 |
| `docker-compose logs -f [service]` | 查看服务日志 |
| `docker-compose restart [service]` | 重启服务 |
| `docker exec -it timescale-db psql -U dbuser -d trading_db` | 进入数据库 |

> **注意**: 所有后端服务必须在 Docker 中运行，不支持本地直接运行

### 前端开发
```bash
cd frontend/trading-panel && pnpm dev
```
访问地址: http://localhost:5173

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

详见 `docs/backend/README.md`

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
- **包管理**: uv (强制使用)
  - 所有 Python 依赖必须通过 `uv` 管理（禁止 pip/poetry/pipenv）
  - 运行脚本必须使用 `uv run`（如 `uv run python script.py`）
  - 安装依赖: `uv add <package>` 或 `uv pip install -r requirements.txt`
  - 同步依赖: `uv sync`
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

### 4.1 类型安全设计原则

**模型贯穿始终**:
- 从业务逻辑到网络传输，全程使用 Pydantic(BaseModel) 模型
- 禁止在响应处理中手动拼装字典
- 响应数据必须使用 Pydantic 模型，禁止传递原始字典

**命名策略**（强制使用基类）:
- **SnakeCaseModel**: 用于接收外部输入，自动将camelCase转为snake_case
  - 例如: `"priceChange"` → `price_change`
  - 适用于解析币安API响应、WebSocket消息等外部数据
- **CamelCaseModel**: 用于响应输出，序列化时自动转为camelCase
  - 例如: `internal_field` → `"internalField"`
  - 适用于API响应、WebSocket推送等对外数据
- 参考实现: `services/{service}/src/models/base.py`

**响应数据模型命名规范**:
- 单个数据: `{Entity}Data` (如 `AlertConfigData`)
- 列表数据: `{Entity}ListData` (如 `AlertConfigListData`)
- 删除响应: `Delete{Entity}Data` (如 `DeleteAlertData`)
- 响应数据: `{Entity}ResponseData` (如 `QuotesResponseData`)

**类型约束**:
- `format_success_response` 的 data 参数类型必须是 `BaseModel`
- `client_manager.send()` 的 message 参数类型必须是 `BaseModel`
- 利用类型系统拦截潜在问题，而非依赖运行时测试

**实践示例**:
```python
# 错误：手动字典拼装（反模式）
return self._response(
    data={"type": "order_list", "orders": orders, "count": len(orders)}
)

# 正确：使用 Pydantic 模型
response_data = OrderListResponseData(orders=order_list, count=len(order_list))
return self._response(data=response_data)
```

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

### 9. 设计优先原则（通用编码规范）

**核心思想**: 模型驱动开发，设计先于实现

**正确流程**: 需求分析 → 数据模型定义 → 文档描述 → 代码实现

#### 设计文档审查流程

在实现任何新功能或修改现有功能前，必须先检查对应的设计文档：

- **WS协议设计**: `docs/backend/design/07-websocket-protocol.md`
- **API模型设计**: `docs/backend/design/08-api-models.md`
- **服务设计**: `docs/backend/design/` 下对应服务的设计文档

审查要点：
- 确认数据模型定义是否完整
- 验证是否使用类型模型而非字典传递
- 检查外部API数据到内部模型的转换流程

**币安服务特殊要求**:
- HTTP/WS客户端返回数据必须先转换为**币安数据模型**
- 再转换为**内部使用的数据模型**
- 全程禁止原始字典传递

**问题警示**:
- ❌ 代码实现 → 文档描述 → 模型依赖实现（本末倒置）
- ✅ 数据模型定义 → 文档描述 → 代码实现（正本清源）

#### 9.1 类型安全（强制约束）

- **禁止原始字典**: 所有数据传递必须使用类型模型
  - Python: Pydantic BaseModel
  - TypeScript: Interface / Type
- **响应拼装反模式**: 禁止 `return {"key": value}`，必须用模型类
- **类型拦截**: 依赖编译期/静态类型检查发现问题，而非运行时测试

#### 9.2 设计文档优先

- 数据模型必须在代码实现前明确定义
- 所有模型变更必须先更新文档，再更新代码
- 如实施中发现设计文档需要改进：
  - 输出改进报告（问题描述、改进方案、影响范围、兼容性评估）
  - 等待审核通过后方可修改代码
  - **禁止自行发挥修改代码**

#### 9.3 实践准则

- **字典是温床**: 字典(dict/map)是"临时解决方案"的温床，最终会导致格式不一致
- **类型即约束**: 类型系统最大的价值不是报错，而是**强制思考和统一**
- **设计即约束**: 强制使用数据模型是一种"设计约束"，可以防止技术债务累积

## 代码结构

详见 `docs/codemaps/` 目录：
- `backend.md` - 后端服务代码结构
- `frontend.md` - 前端代码结构
- `architecture.md` - 架构代码结构
- `data.md` - 数据层代码结构

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

### Docker操作

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | 启动所有服务 |
| `docker-compose down` | 停止所有服务 |
| `docker-compose logs -f [service]` | 查看日志 |
| `docker-compose restart [service]` | 重启服务 |
| `docker exec -it [container] /bin/bash` | 进入容器 |

### 数据库调试

```bash
# 进入容器
docker exec -it timescale-db /bin/bash

# 连接数据库
psql -U dbuser -d trading_db
```

**连接信息**: Host: `timescale-db`, DB: `trading_db`, User: `dbuser`, Pass: `pass`, Port: `5432`

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
- **代码风格**: ruff + 类型注解
- **日志**: 结构化JSON日志
- **安全**: 敏感信息使用环境变量，参数化查询

## 文档阅读指南

1. 阅读 `docs/backend/README.md` 了解文档体系
2. 阅读 `docs/backend/design/DATABASE_COORDINATED_ARCHITECTURE.md` 理解设计理念
3. 阅读 `docs/backend/design/QUANT_TRADING_SYSTEM_ARCHITECTURE.md` 掌握实施细节

> 任何架构决策必须参考核心理念文档，任何实现方案必须参考实施文档