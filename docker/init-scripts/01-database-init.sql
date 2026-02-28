-- =============================================================================
-- 量化交易系统数据库初始化脚本
-- TimescaleDB: timescale/timescaledb:latest-pg18
-- PostgreSQL: 18
-- 架构: 事件驱动 + PostgreSQL NOTIFY/LISTEN + TimescaleDB Hypertable
-- =============================================================================
--
-- 执行方式:
--   psql -U dbuser -d trading_db -f 01-database-init.sql
--
-- 注意事项:
--   - TimescaleDB 2.14+ 在 PostgreSQL 18 上使用最新语法
--   - 所有表在创建后立即转换为 Hypertable
--   - 保留策略使用 named parameter 语法 (drop_after => INTERVAL)
--
-- =============================================================================

-- =============================================================================
-- 第一部分: 启用扩展
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- =============================================================================
-- 第二部分: 删除旧表（如果有）
-- =============================================================================
DROP TABLE IF EXISTS klines_live CASCADE;
DROP TABLE IF EXISTS klines CASCADE;
DROP TABLE IF EXISTS task_queue CASCADE;
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS strategy_signals CASCADE;
DROP TABLE IF EXISTS alert_configs CASCADE;
DROP TABLE IF EXISTS subscription_keys CASCADE;
DROP TABLE IF EXISTS task_results CASCADE;

-- =============================================================================
-- 第三部分: 创建表
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 3.1 realtime_data 实时数据表
-- 设计: 状态表，每个订阅键只有一条记录，使用 UNIQUE (subscription_key) 约束
-- 注意: 这是普通表（非 TimescaleDB 超表），因为是状态表不需要时间分区
-- -----------------------------------------------------------------------------
CREATE TABLE realtime_data (
    id BIGSERIAL PRIMARY KEY,

    -- 订阅键格式：{EXCHANGE}:{SYMBOL}[.{产品后缀}]@{DATA_TYPE}[_{RESOLUTION}]
    -- 示例: BINANCE:BTCUSDT@KLINE_1, BINANCE:BTCUSDT@QUOTES
    -- 注意：interval 使用 TradingView 官方格式（1, 5, 15, 60, 240, D, W, M）
    subscription_key VARCHAR(255) NOT NULL UNIQUE,

    -- 数据类型: KLINE, QUOTES, TRADE
    data_type VARCHAR(50) NOT NULL,

    -- 实时数据（格式由币安服务决定）
    data JSONB NOT NULL,

    -- 事件时间
    event_time TIMESTAMPTZ,

    -- 订阅源数组（用于区分不同服务的订阅）
    -- api-service 表示 API 网关的前端订阅
    -- signal-service 表示信号服务的订阅
    subscribers TEXT[] DEFAULT '{}',

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_realtime_data_data_type ON realtime_data (data_type);
CREATE INDEX IF NOT EXISTS idx_realtime_data_subscribers ON realtime_data USING GIN (subscribers);
CREATE INDEX IF NOT EXISTS idx_realtime_data_updated ON realtime_data (updated_at DESC);

-- -----------------------------------------------------------------------------
-- 3.2 tasks 任务表
-- 设计: 一次性请求任务，INSERT触发task_new，UPDATE status=completed触发task_completed
-- -----------------------------------------------------------------------------
CREATE TABLE tasks (
    id BIGSERIAL PRIMARY KEY,

    -- 任务类型: get_klines, get_server_time, get_quotes, system.fetch_exchange_info
    type VARCHAR(50) NOT NULL,

    -- 任务参数（JSON格式）
    payload JSONB NOT NULL DEFAULT '{}',

    -- 任务结果（币安服务填写）
    result JSONB,

    -- 任务状态: pending, processing, completed, failed
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks (type);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks (created_at DESC);

-- 转换为 Hypertable
SELECT create_hypertable('tasks', 'created_at');

-- -----------------------------------------------------------------------------
-- 3.4 account_info 账户信息表
-- 设计: 存储现货/期货账户原始数据，binance-service写入，api-service查询后推送
-- 写入策略: INSERT ... ON CONFLICT (account_type) DO UPDATE 覆盖更新
-- 参考文档: docs/backend/design/01-task-subscription.md 章节 2.2
-- -----------------------------------------------------------------------------
CREATE TABLE account_info (
    id BIGSERIAL PRIMARY KEY,

    -- 账户类型: SPOT, FUTURES
    account_type VARCHAR(20) NOT NULL,

    -- 原始数据（完整保存，前端自行解析）
    data JSONB NOT NULL,

    -- 币安返回的更新时间
    update_time BIGINT,

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- 唯一约束（每个账户类型只有一条记录）
    UNIQUE(account_type)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_account_info_type ON account_info (account_type);

-- -----------------------------------------------------------------------------
-- 3.3 klines_history K线历史表
-- 设计: 扁平化存储已闭合的K线数据，通过trigger_archive_closed_kline触发器自动归档
-- -----------------------------------------------------------------------------
CREATE TABLE klines_history (
    id BIGSERIAL PRIMARY KEY,

    -- 扁平化K线字段
    symbol TEXT NOT NULL,                    -- 格式: BINANCE:BTCUSDT, BINANCE:BTCUSDT.PERP
    interval TEXT NOT NULL,                  -- 格式: TV格式（1, 5, 15, 60, 240, D, W, M）
    open_time TIMESTAMPTZ NOT NULL,
    close_time TIMESTAMPTZ NOT NULL,
    open_price NUMERIC(24,12) NOT NULL,
    high_price NUMERIC(24,12) NOT NULL,
    low_price NUMERIC(24,12) NOT NULL,
    close_price NUMERIC(24,12) NOT NULL,
    volume NUMERIC(24,12) NOT NULL,
    quote_volume NUMERIC(24,12) NOT NULL,
    number_of_trades INTEGER NOT NULL,
    taker_buy_base_volume NUMERIC(24,12) NOT NULL,
    taker_buy_quote_volume NUMERIC(24,12) NOT NULL,

    -- 归档时间
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- 唯一约束（必须包含所有分区键）
    CONSTRAINT uk_klines_history UNIQUE (symbol, open_time, interval)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_klines_history_symbol_time
    ON klines_history (symbol, open_time DESC);
CREATE INDEX IF NOT EXISTS idx_klines_history_interval
    ON klines_history (interval);

-- 转换为 Hypertable
SELECT create_hypertable('klines_history', 'open_time');

-- -----------------------------------------------------------------------------
-- 3.4 exchange_info 交易所信息表
-- 设计: 存储币安交易所的交易对信息，支持SPOT和FUTURES
-- -----------------------------------------------------------------------------
CREATE TABLE exchange_info (
    id BIGSERIAL PRIMARY KEY,

    -- 基本信息
    exchange VARCHAR(50) NOT NULL DEFAULT 'BINANCE',
    market_type VARCHAR(20) NOT NULL,           -- SPOT, FUTURES
    symbol VARCHAR(50) NOT NULL,
    base_asset VARCHAR(20) NOT NULL,
    quote_asset VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'TRADING',

    -- 精度信息
    base_asset_precision INTEGER NOT NULL DEFAULT 8,
    quote_precision INTEGER NOT NULL DEFAULT 8,
    quote_asset_precision INTEGER NOT NULL DEFAULT 8,
    base_commission_precision INTEGER NOT NULL DEFAULT 8,
    quote_commission_precision INTEGER NOT NULL DEFAULT 8,

    -- 交易规则过滤器
    filters JSONB NOT NULL DEFAULT '{}',

    -- 交易选项
    order_types JSONB NOT NULL DEFAULT '[]',
    permissions JSONB NOT NULL DEFAULT '[]',

    -- 特殊选项
    iceberg_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    oco_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    oto_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    opo_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    quote_order_qty_market_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    allow_trailing_stop BOOLEAN NOT NULL DEFAULT FALSE,
    cancel_replace_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    amend_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    peg_instructions_allowed BOOLEAN NOT NULL DEFAULT FALSE,

    -- 交易权限
    is_spot_trading_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    is_margin_trading_allowed BOOLEAN NOT NULL DEFAULT FALSE,

    -- 权限管理
    permission_sets JSONB NOT NULL DEFAULT '[]',

    -- 自成交防护
    default_self_trade_prevention_mode VARCHAR NOT NULL DEFAULT 'NONE',
    allowed_self_trade_prevention_modes JSONB NOT NULL DEFAULT '[]',

    -- 更新时间
    last_updated TIMESTAMPTZ DEFAULT NOW(),

    -- 唯一约束
    CONSTRAINT uk_exchange_info UNIQUE (exchange, market_type, symbol)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_exchange_info_symbol ON exchange_info (symbol);
CREATE INDEX IF NOT EXISTS idx_exchange_info_market ON exchange_info (market_type);

-- -----------------------------------------------------------------------------
-- 3.5 alert_configs 告警配置表
-- 设计: 存储告警规则配置，INSERT/UPDATE/DELETE触发配置变更通知
-- 用于MACD共振策略等多策略系统的配置管理，支持按用户/策略/参数索引查询
-- 注意: id 由前端生成 UUIDv4，所有字段都可重复
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alert_configs (
    id VARCHAR(36) PRIMARY KEY,  -- 前端生成的 UUIDv4（如 "0189a1b2-c3d4-5e6f-7890-abcd12345678"）

    -- 告警信息
    name VARCHAR(100) NOT NULL,              -- 告警名称（用户友好，可重复）
    description TEXT,                          -- 告警描述

    -- 策略类型（便于按策略类型索引和筛选）
    strategy_type VARCHAR(50) NOT NULL,      -- 策略类型，如 "macd_resonance", "rsi_oversold"

    -- 交易对和周期
    symbol VARCHAR(50) NOT NULL,              -- 交易对：如 "BINANCE:BTCUSDT"
    interval VARCHAR(10) NOT NULL,             -- K线周期：TradingView格式 (1, 5, 15, 60, 240, D, W, M)

    -- 触发条件类型
    trigger_type VARCHAR(20) NOT NULL DEFAULT 'each_kline_close',
    -- - once_only: 仅执行一次
    -- - each_kline: 每个K线触发
    -- - each_kline_close: 每个K线闭合时触发
    -- - each_minute: 每分钟触发

    -- 策略参数（JSON格式存储，支持任意策略类型）
    params JSONB NOT NULL DEFAULT '{}',        -- 策略参数，如 {"fast1": 12, "slow1": 26, "signal1": 9}

    -- 告警状态
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,

    -- 用户标识（便于按用户索引和筛选）
    created_by VARCHAR(100),                   -- 创建者标识

    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()

    -- 注意: 所有字段都可重复，唯一标识为 id
);

-- 复合索引：按用户 + 策略类型查询
CREATE INDEX IF NOT EXISTS idx_alerts_user_strategy
    ON alert_configs (created_by, strategy_type);

-- 复合索引：按用户 + 交易对查询
CREATE INDEX IF NOT EXISTS idx_alerts_user_symbol
    ON alert_configs (created_by, symbol);

-- 复合索引：按策略类型 + 交易对查询
CREATE INDEX IF NOT EXISTS idx_alerts_strategy_symbol
    ON alert_configs (strategy_type, symbol);

-- GIN 索引：按参数查询（支持参数维度筛选）
CREATE INDEX IF NOT EXISTS idx_alerts_params_gin
    ON alert_configs USING GIN (params jsonb_path_ops);

-- 索引：按启用状态查询（批量处理时使用）
CREATE INDEX IF NOT EXISTS idx_alerts_enabled
    ON alert_configs (is_enabled) WHERE is_enabled = TRUE;

-- -----------------------------------------------------------------------------
-- 3.6 strategy_signals 策略信号表
-- 设计: 存储策略计算产生的信号，INSERT触发signal.new通知
-- 用于追踪历史信号记录，支持按用户/策略索引查询
-- 注意: id (BIGSERIAL) 作为唯一标识
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS strategy_signals (
    id BIGSERIAL PRIMARY KEY,

    -- 关联告警（用于追溯配置来源）
    alert_id VARCHAR(36) NOT NULL,   -- 关联 alert_configs.id（前端生成）

    -- 用户标识
    created_by VARCHAR(100),                   -- 创建者标识

    -- 策略信息
    strategy_type VARCHAR(50) NOT NULL,       -- 策略类型，如 "macd_resonance", "rsi_oversold"
    symbol VARCHAR(50) NOT NULL,               -- 交易对，如 "BINANCE:BTCUSDT"
    interval VARCHAR(10) NOT NULL,             -- K线周期，如 "1", "5", "60"

    -- 触发类型（与 alert_configs.trigger_type 对应）
    trigger_type VARCHAR(20) NOT NULL DEFAULT 'each_kline_close',
    -- - once_only: 仅执行一次
    -- - each_kline: 每个K线触发
    -- - each_kline_close: 每个K线闭合时触发
    -- - each_minute: 每分钟触发

    -- 信号结果
    signal_value BOOLEAN NOT NULL,             -- 信号值：true(做多) / false(做空) / null(无信号)
    signal_reason TEXT,                        -- 信号原因：如"建仓信号"、"清仓信号"、"无信号"

    -- 元数据
    computed_at TIMESTAMPTZ DEFAULT NOW(),  -- 信号计算时间
    source_subscription_key VARCHAR(255),   -- 触发该信号的订阅键
    metadata JSONB DEFAULT '{}'                -- 额外元数据
);

-- 复合索引：按用户 + 策略类型 + 时间查询（用户追踪检查）
CREATE INDEX IF NOT EXISTS idx_signals_user_strategy_time
    ON strategy_signals (created_by, strategy_type, computed_at DESC);

-- 复合索引：按用户 + 交易对 + 时间查询（用户查看特定交易对信号）
CREATE INDEX IF NOT EXISTS idx_signals_user_symbol_time
    ON strategy_signals (created_by, symbol, computed_at DESC);

-- 复合索引：按告警 ID 查询（查看特定告警的所有信号）
CREATE INDEX IF NOT EXISTS idx_signals_alert_id
    ON strategy_signals (alert_id, computed_at DESC);

-- 复合索引：按策略类型 + 交易对 + 时间查询（分析特定策略表现）
CREATE INDEX IF NOT EXISTS idx_signals_strategy_symbol_time
    ON strategy_signals (strategy_type, symbol, computed_at DESC);

-- 转换为 Hypertable（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM _timescaledb_catalog.hypertable WHERE table_name = 'strategy_signals') THEN
        PERFORM create_hypertable('strategy_signals', 'computed_at');
    END IF;
END $$;

-- 索引：按计算时间查询
CREATE INDEX IF NOT EXISTS idx_strategy_signals_computed
    ON strategy_signals (computed_at DESC);

-- =============================================================================
-- 第四部分: 触发器函数
-- =============================================================================

-- 任务创建通知：INSERT tasks时触发，通知币安服务有新任务（统一包装格式）
CREATE OR REPLACE FUNCTION notify_task_new()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('task.new', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'task.new',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'id', NEW.id,
            'type', NEW.type,
            'payload', NEW.payload,
            'status', NEW.status,
            'created_at', NEW.created_at::TEXT
        )
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 任务状态变更通知：UPDATE tasks.status变更时触发，通知API网关（统一包装格式）
-- 支持 completed 和 failed 两种状态
CREATE OR REPLACE FUNCTION notify_task_status_change()
RETURNS TRIGGER AS $$
DECLARE
    event_type TEXT;
BEGIN
    -- 确定事件类型
    IF NEW.status = 'completed' THEN
        event_type := 'task.completed';
    ELSIF NEW.status = 'failed' THEN
        event_type := 'task.failed';
    ELSE
        -- 其他状态不发送通知
        RETURN NEW;
    END IF;

    PERFORM pg_notify(event_type, jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', event_type,
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'id', NEW.id,
            'type', NEW.type,
            'payload', NEW.payload,
            'result', NEW.result,
            'status', NEW.status,
            'updated_at', NEW.updated_at::TEXT
        )
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 新增订阅通知：INSERT realtime_data时触发，通知币安服务（统一包装格式）
-- 注意：INSERT 时只发送 subscription.add 通知，不发送 realtime.update
-- 原因：INSERT 时 data 字段为空对象 '{}'，推送空数据给客户端没有意义
-- realtime.update 只在 UPDATE 时发送（当数据实际变化时）
CREATE OR REPLACE FUNCTION notify_subscription_add()
RETURNS TRIGGER AS $$
BEGIN
    -- 发送 subscription.add 通知给 api-service（用于前端订阅）
    -- 发送 binance-service（用于订阅币安WS）
    PERFORM pg_notify('subscription.add', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'subscription.add',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'subscription_key', NEW.subscription_key,
            'data_type', NEW.data_type,
            'created_at', NOW()::TEXT
        )
    )::TEXT);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 实时数据更新通知：UPDATE realtime_data.data时触发，通知signal-service
CREATE OR REPLACE FUNCTION notify_realtime_update()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('realtime.update', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'realtime.update',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'subscription_key', NEW.subscription_key,
            'data_type', NEW.data_type,
            'data', NEW.data,
            'event_time', NEW.event_time::TEXT
        )
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 取消订阅通知：DELETE realtime_data时触发，通知币安服务（统一包装格式）
CREATE OR REPLACE FUNCTION notify_subscription_remove()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('subscription.remove', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'subscription.remove',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'subscription_key', OLD.subscription_key,
            'data_type', OLD.data_type,
            'created_at', NOW()::TEXT
        )
    )::TEXT);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- 清空所有订阅通知：TRUNCATE realtime_data时触发（API网关重启）（统一包装格式）
CREATE OR REPLACE FUNCTION notify_subscription_clean()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('subscription.clean', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'subscription.clean',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'action', 'clean_all'
        )
    )::TEXT);
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 归档已关闭的K线：UPDATE realtime_data时触发，自动归档到klines_history
-- 实时K线数据更准确，有冲突时使用实时数据更新
CREATE OR REPLACE FUNCTION archive_closed_kline()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.data_type = 'KLINE' AND (NEW.data->'k'->>'x')::boolean = true THEN
        INSERT INTO klines_history (
            symbol, interval,
            open_time, close_time,
            open_price, high_price, low_price, close_price,
            volume, quote_volume, number_of_trades,
            taker_buy_base_volume, taker_buy_quote_volume
        )
        VALUES (
            'BINANCE:' || (NEW.data->>'s'),                                    -- symbol: 需添加"BINANCE:"前缀
            CASE (NEW.data->'k'->>'i')
                WHEN '1m' THEN '1'
                WHEN '3m' THEN '3'
                WHEN '5m' THEN '5'
                WHEN '15m' THEN '15'
                WHEN '30m' THEN '30'
                WHEN '1h' THEN '60'
                WHEN '2h' THEN '120'
                WHEN '4h' THEN '240'
                WHEN '6h' THEN '360'
                WHEN '8h' THEN '480'
                WHEN '12h' THEN '720'
                WHEN '1d' THEN '1D'
                WHEN '3d' THEN '3D'
                WHEN '1w' THEN '1W'
                WHEN '1M' THEN '1M'
                ELSE (NEW.data->'k'->>'i')
            END,                                                                  -- interval: 转换为TV格式
            to_timestamp((NEW.data->'k'->>'t')::bigint / 1000),             -- open_time (毫秒转秒)
            to_timestamp((NEW.data->'k'->>'T')::bigint / 1000),             -- close_time (毫秒转秒)
            (NEW.data->'k'->>'o')::numeric,                                  -- open_price
            (NEW.data->'k'->>'h')::numeric,                                  -- high_price
            (NEW.data->'k'->>'l')::numeric,                                  -- low_price
            (NEW.data->'k'->>'c')::numeric,                                  -- close_price
            (NEW.data->'k'->>'v')::numeric,                                  -- volume
            (NEW.data->'k'->>'q')::numeric,                                  -- quote_volume
            (NEW.data->'k'->>'n')::integer,                                  -- number_of_trades
            (NEW.data->'k'->>'V')::numeric,                                  -- taker_buy_base_volume
            (NEW.data->'k'->>'Q')::numeric                                   -- taker_buy_quote_volume
        )
        ON CONFLICT (symbol, open_time, interval) DO UPDATE SET
            close_time = EXCLUDED.close_time,
            open_price = EXCLUDED.open_price,
            high_price = EXCLUDED.high_price,
            low_price = EXCLUDED.low_price,
            close_price = EXCLUDED.close_price,
            volume = EXCLUDED.volume,
            quote_volume = EXCLUDED.quote_volume,
            number_of_trades = EXCLUDED.number_of_trades,
            taker_buy_base_volume = EXCLUDED.taker_buy_base_volume,
            taker_buy_quote_volume = EXCLUDED.taker_buy_quote_volume;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 信号生成通知：INSERT strategy_signals时触发，通知API网关或交易系统（统一包装格式）
CREATE OR REPLACE FUNCTION notify_signal_new()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('signal.new', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'signal.new',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'id', NEW.id,
            'alert_id', NEW.alert_id,
            'created_by', NEW.created_by,
            'strategy_type', NEW.strategy_type,
            'symbol', NEW.symbol,
            'interval', NEW.interval,
            'trigger_type', NEW.trigger_type,
            'signal_value', NEW.signal_value,
            'signal_reason', NEW.signal_reason,
            'computed_at', NEW.computed_at::TEXT
        )
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- 告警配置通知函数（使用 alert_configs 表）
-- -----------------------------------------------------------------------------

-- 告警配置新增通知：INSERT alert_configs 时触发（仅当 is_enabled=true）
CREATE OR REPLACE FUNCTION notify_alert_config_new()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_enabled = TRUE THEN
        PERFORM pg_notify('alert_config.new', jsonb_build_object(
            'event_id', uuidv7()::TEXT,
            'event_type', 'alert_config.new',
            'timestamp', NOW()::TEXT,
            'data', jsonb_build_object(
                'id', NEW.id,
                'name', NEW.name,
                'description', NEW.description,
                'strategy_type', NEW.strategy_type,
                'symbol', NEW.symbol,
                'interval', NEW.interval,
                'trigger_type', NEW.trigger_type,
                'params', NEW.params,
                'is_enabled', NEW.is_enabled,
                'created_by', NEW.created_by,
                'created_at', NEW.created_at::TEXT
            )
        )::TEXT);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 告警配置更新通知：UPDATE alert_configs 时触发
CREATE OR REPLACE FUNCTION notify_alert_config_update()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('alert_config.update', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'alert_config.update',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'id', NEW.id,
            'name', NEW.name,
            'description', NEW.description,
            'strategy_type', NEW.strategy_type,
            'symbol', NEW.symbol,
            'interval', NEW.interval,
            'trigger_type', NEW.trigger_type,
            'params', NEW.params,
            'is_enabled', NEW.is_enabled,
            'updated_at', NEW.updated_at::TEXT,
            'created_by', NEW.created_by
        )
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 告警配置删除通知：DELETE alert_configs 时触发
CREATE OR REPLACE FUNCTION notify_alert_config_delete()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('alert_config.delete', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'alert_config.delete',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'id', OLD.id,
            'name', OLD.name,
            'strategy_type', OLD.strategy_type,
            'symbol', OLD.symbol,
            'interval', OLD.interval,
            'deleted_at', NOW()::TEXT
        )
    )::TEXT);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 第五部分: 创建触发器
-- =============================================================================

-- tasks 触发器
DROP TRIGGER IF EXISTS trigger_task_new ON tasks;
CREATE TRIGGER trigger_task_new
    AFTER INSERT ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION notify_task_new();

DROP TRIGGER IF EXISTS trigger_task_completed ON tasks;
CREATE TRIGGER trigger_task_completed
    AFTER UPDATE ON tasks
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status AND NEW.status IN ('completed', 'failed'))
    EXECUTE FUNCTION notify_task_status_change();

-- realtime_data 触发器
DROP TRIGGER IF EXISTS trigger_realtime_data_add ON realtime_data;
CREATE TRIGGER trigger_realtime_data_add
    AFTER INSERT ON realtime_data
    FOR EACH ROW
    EXECUTE FUNCTION notify_subscription_add();

DROP TRIGGER IF EXISTS trigger_realtime_data_update ON realtime_data;
CREATE TRIGGER trigger_realtime_data_update
    AFTER UPDATE ON realtime_data
    FOR EACH ROW
    WHEN (OLD.data IS DISTINCT FROM NEW.data)
    EXECUTE FUNCTION notify_realtime_update();

DROP TRIGGER IF EXISTS trigger_realtime_data_remove ON realtime_data;
CREATE TRIGGER trigger_realtime_data_remove
    AFTER DELETE ON realtime_data
    FOR EACH ROW
    EXECUTE FUNCTION notify_subscription_remove();

DROP TRIGGER IF EXISTS trigger_realtime_data_clean ON realtime_data;
CREATE TRIGGER trigger_realtime_data_clean
    AFTER TRUNCATE ON realtime_data
    FOR EACH STATEMENT
    EXECUTE FUNCTION notify_subscription_clean();

-- K线归档触发器
DROP TRIGGER IF EXISTS trigger_archive_closed_kline ON realtime_data;
CREATE TRIGGER trigger_archive_closed_kline
    AFTER UPDATE ON realtime_data
    FOR EACH ROW
    WHEN (NEW.data_type = 'KLINE' AND (NEW.data->'k'->>'x')::boolean = true)
    EXECUTE FUNCTION archive_closed_kline();

-- strategy_signals 触发器
DROP TRIGGER IF EXISTS trigger_strategy_signals_new ON strategy_signals;
CREATE TRIGGER trigger_strategy_signals_new
    AFTER INSERT ON strategy_signals
    FOR EACH ROW
    EXECUTE FUNCTION notify_signal_new();

-- alert_configs 触发器（替代原有的 strategy_configurations 触发器）
DROP TRIGGER IF EXISTS trigger_alert_config_new ON alert_configs;
CREATE TRIGGER trigger_alert_config_new
    AFTER INSERT ON alert_configs
    FOR EACH ROW
    EXECUTE FUNCTION notify_alert_config_new();

DROP TRIGGER IF EXISTS trigger_alert_config_update ON alert_configs;
CREATE TRIGGER trigger_alert_config_update
    AFTER UPDATE ON alert_configs
    FOR EACH ROW
    EXECUTE FUNCTION notify_alert_config_update();

DROP TRIGGER IF EXISTS trigger_alert_config_delete ON alert_configs;
CREATE TRIGGER trigger_alert_config_delete
    AFTER DELETE ON alert_configs
    FOR EACH ROW
    EXECUTE FUNCTION notify_alert_config_delete();

-- =============================================================================
-- 第六部分: 数据保留策略
-- =============================================================================
--
-- TimescaleDB 保留策略使用 named parameter 语法
-- 注意: klines_history 永久保留，不设置保留策略
-- 注意: add_retention_policy 会自动跳过已存在的策略，无需手动检查
--

-- tasks: 保留7天
PERFORM add_retention_policy('tasks', drop_after => INTERVAL '7 days');

-- realtime_data: 保留1天（实时数据，及时清理）
PERFORM add_retention_policy('realtime_data', drop_after => INTERVAL '1 day');

-- strategy_signals: 保留30天（策略信号需要长期跟踪）
PERFORM add_retention_policy('strategy_signals', drop_after => INTERVAL '30 days');

-- =============================================================================
-- 第七部分: upsert_exchange_info 存储过程
-- =============================================================================
--
-- 用于交易所信息的全量替换，支持ON CONFLICT DO UPDATE
--
CREATE OR REPLACE FUNCTION upsert_exchange_info(
    p_exchange VARCHAR,
    p_market_type VARCHAR,
    p_symbol VARCHAR,
    p_base_asset VARCHAR,
    p_quote_asset VARCHAR,
    p_status VARCHAR,

    p_base_asset_precision INTEGER DEFAULT 8,
    p_quote_precision INTEGER DEFAULT 8,
    p_quote_asset_precision INTEGER DEFAULT 8,
    p_base_commission_precision INTEGER DEFAULT 8,
    p_quote_commission_precision INTEGER DEFAULT 8,

    p_filters JSONB DEFAULT '{}',
    p_order_types JSONB DEFAULT '[]',
    p_permissions JSONB DEFAULT '[]',

    p_iceberg_allowed BOOLEAN DEFAULT FALSE,
    p_oco_allowed BOOLEAN DEFAULT FALSE,
    p_oto_allowed BOOLEAN DEFAULT FALSE,
    p_opo_allowed BOOLEAN DEFAULT FALSE,
    p_quote_order_qty_market_allowed BOOLEAN DEFAULT FALSE,
    p_allow_trailing_stop BOOLEAN DEFAULT FALSE,
    p_cancel_replace_allowed BOOLEAN DEFAULT FALSE,
    p_amend_allowed BOOLEAN DEFAULT FALSE,
    p_peg_instructions_allowed BOOLEAN DEFAULT FALSE,

    p_is_spot_trading_allowed BOOLEAN DEFAULT TRUE,
    p_is_margin_trading_allowed BOOLEAN DEFAULT FALSE,

    p_permission_sets JSONB DEFAULT '[]',

    p_default_self_trade_prevention_mode VARCHAR DEFAULT 'NONE',
    p_allowed_self_trade_prevention_modes JSONB DEFAULT '[]'
) RETURNS BIGINT AS $$
DECLARE
    v_id BIGINT;
BEGIN
    INSERT INTO exchange_info (
        exchange, market_type, symbol, base_asset, quote_asset, status,
        base_asset_precision, quote_precision, quote_asset_precision,
        base_commission_precision, quote_commission_precision,
        filters, order_types, permissions,
        iceberg_allowed, oco_allowed, oto_allowed, opo_allowed,
        quote_order_qty_market_allowed, allow_trailing_stop,
        cancel_replace_allowed, amend_allowed, peg_instructions_allowed,
        is_spot_trading_allowed, is_margin_trading_allowed,
        permission_sets,
        default_self_trade_prevention_mode, allowed_self_trade_prevention_modes,
        last_updated
    ) VALUES (
        p_exchange, p_market_type, p_symbol, p_base_asset, p_quote_asset, p_status,
        COALESCE(p_base_asset_precision, 8), COALESCE(p_quote_precision, 8),
        COALESCE(p_quote_asset_precision, 8), COALESCE(p_base_commission_precision, 8),
        COALESCE(p_quote_commission_precision, 8),
        p_filters, p_order_types, p_permissions,
        p_iceberg_allowed, p_oco_allowed, p_oto_allowed, p_opo_allowed,
        p_quote_order_qty_market_allowed, p_allow_trailing_stop,
        p_cancel_replace_allowed, p_amend_allowed, p_peg_instructions_allowed,
        p_is_spot_trading_allowed, p_is_margin_trading_allowed,
        p_permission_sets,
        p_default_self_trade_prevention_mode, p_allowed_self_trade_prevention_modes,
        NOW()
    )
    ON CONFLICT (exchange, market_type, symbol) DO UPDATE SET
        base_asset = p_base_asset,
        quote_asset = p_quote_asset,
        status = p_status,
        base_asset_precision = COALESCE(p_base_asset_precision, 8),
        quote_precision = COALESCE(p_quote_precision, 8),
        quote_asset_precision = COALESCE(p_quote_asset_precision, 8),
        base_commission_precision = COALESCE(p_base_commission_precision, 8),
        quote_commission_precision = COALESCE(p_quote_commission_precision, 8),
        filters = p_filters,
        order_types = p_order_types,
        permissions = p_permissions,
        iceberg_allowed = p_iceberg_allowed,
        oco_allowed = p_oco_allowed,
        oto_allowed = p_oto_allowed,
        opo_allowed = p_opo_allowed,
        quote_order_qty_market_allowed = p_quote_order_qty_market_allowed,
        allow_trailing_stop = p_allow_trailing_stop,
        cancel_replace_allowed = p_cancel_replace_allowed,
        amend_allowed = p_amend_allowed,
        peg_instructions_allowed = p_peg_instructions_allowed,
        is_spot_trading_allowed = p_is_spot_trading_allowed,
        is_margin_trading_allowed = p_is_margin_trading_allowed,
        permission_sets = p_permission_sets,
        default_self_trade_prevention_mode = p_default_self_trade_prevention_mode,
        allowed_self_trade_prevention_modes = p_allowed_self_trade_prevention_modes,
        last_updated = NOW()
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 第八部分: 通知频道说明
-- =============================================================================
--
-- | 频道                   | 触发条件                    | 发送者  | 接收者         | 说明                    |
-- |-----------------------|----------------------------|---------|----------------|-------------------------|
-- | task.new              | INSERT tasks               | 数据库  | 币安服务       | 新任务通知              |
-- | task.completed        | UPDATE status=completed    | 数据库  | API网关        | 任务完成通知            |
-- | subscription.add      | INSERT realtime_data        | 数据库  | 币安服务       | 新增订阅通知            |
-- | subscription.remove   | DELETE realtime_data        | 数据库  | 币安服务       | 取消订阅通知            |
-- | subscription.clean    | TRUNCATE realtime_data     | 数据库  | 币安服务       | 清空所有订阅（重启）    |
-- | realtime.update       | UPDATE realtime_data        | 数据库  | API网关/信号服务 | 实时数据更新通知     |
-- | signal.new            | INSERT strategy_signals     | 数据库  | API网关/交易系统 | 新信号生成通知       |
-- | alert_config.new      | INSERT alert_configs        | 数据库  | 信号服务       | 新建告警配置通知       |
-- | alert_config.update   | UPDATE alert_configs        | 数据库  | 信号服务       | 更新告警配置通知       |
-- | alert_config.delete   | DELETE alert_configs        | 数据库  | 信号服务       | 删除告警配置通知       |
--
-- =============================================================================
-- 策略元数据表（由 signal-service 自动维护）
-- =============================================================================
CREATE TABLE IF NOT EXISTS alert_strategy_metadata (
    type VARCHAR(100) PRIMARY KEY,  -- 策略类型标识符（类名）
    name VARCHAR(255) NOT NULL,      -- 策略显示名称
    description TEXT,                -- 策略描述
    params JSONB NOT NULL,          -- 策略参数定义
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE alert_strategy_metadata IS '策略元数据表，由signal-service启动时自动同步';

-- =============================================================================
-- 初始化完成
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE '数据库初始化完成！';
    RAISE NOTICE '========================================';
    RAISE NOTICE '表: realtime_data, tasks, klines_history, exchange_info, alert_configs, strategy_signals';
    RAISE NOTICE 'Hypertable: 4个表已转换为TimescaleDB Hypertable';
    RAISE NOTICE '触发器: 11个触发器已创建';
    RAISE NOTICE '保留策略: tasks(7天), realtime_data(1天), strategy_signals(30天)';
    RAISE NOTICE '通知频道: task.new, task.completed, subscription.add, subscription.remove, subscription.clean, realtime.update, signal.new, alert_config.new, alert_config.update, alert_config.delete';
    RAISE NOTICE '========================================';
END $$;
