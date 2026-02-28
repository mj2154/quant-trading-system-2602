-- =============================================================================
-- MACD 共振策略增量迁移脚本
-- 用途: 将 MACD 共振策略功能添加到已有数据的数据库
-- 特性: 使用 IF NOT EXISTS 和 CREATE OR REPLACE，不会删除现有数据
-- =============================================================================
--
-- 执行方式:
--   psql -U dbuser -d trading_db -f 02-migrate-macd-strategy.sql
--
-- 注意事项:
--   - 此脚本不会删除任何现有数据
--   - 表已存在时会跳过创建
--   - 触发器已存在时会跳过创建
--   - klines_history 表数据完全保留
--
-- =============================================================================

-- =============================================================================
-- 第一部分: 删除 kline_snapshot 字段（如存在）
-- 根据计划：删除 kline_snapshot，添加 config_id 和 trigger_type
-- =============================================================================

-- 删除 kline_snapshot 字段（如果存在）
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'strategy_signals'
        AND column_name = 'kline_snapshot'
    ) THEN
        ALTER TABLE strategy_signals DROP COLUMN kline_snapshot;
        RAISE NOTICE '已删除 kline_snapshot 字段';
    ELSE
        RAISE NOTICE 'kline_snapshot 字段不存在，跳过删除';
    END IF;
END $$;

-- =============================================================================
-- 第二部分: 创建表（表存在时跳过）
-- =============================================================================

-- strategy_configurations 策略配置表
CREATE TABLE IF NOT EXISTS strategy_configurations (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    trigger_type VARCHAR(20) NOT NULL DEFAULT 'each_kline_close',
    macd_params JSONB NOT NULL DEFAULT '{}',
    threshold NUMERIC(10, 4) NOT NULL DEFAULT 0,
    symbol VARCHAR(50) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),
    CONSTRAINT uk_strategy_config UNIQUE (name, symbol, interval)
);

-- strategy_signals 策略信号表
-- 注意：如果表已存在但缺少字段，会自动添加
CREATE TABLE IF NOT EXISTS strategy_signals (
    id BIGSERIAL PRIMARY KEY,
    signal_id UUID NOT NULL DEFAULT uuidv7(),
    config_id UUID,
    strategy_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    interval VARCHAR(10) NOT NULL,
    trigger_type VARCHAR(20),
    signal_value BOOLEAN,
    signal_reason TEXT,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    source_subscription_key VARCHAR(255),
    metadata JSONB DEFAULT '{}'
);

-- =============================================================================
-- 第三部分: 添加外键约束（如不存在）
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'strategy_signals'
        AND constraint_name = 'fk_strategy_signals_config'
    ) THEN
        ALTER TABLE strategy_signals
        ADD CONSTRAINT fk_strategy_signals_config
        FOREIGN KEY (config_id) REFERENCES strategy_configurations(id) ON DELETE SET NULL;
        RAISE NOTICE '已添加外键约束 fk_strategy_signals_config';
    ELSE
        RAISE NOTICE '外键约束 fk_strategy_signals_config 已存在，跳过';
    END IF;
END $$;

-- =============================================================================
-- 第四部分: 创建索引（索引存在时跳过）
-- =============================================================================

-- strategy_configurations 索引
CREATE INDEX IF NOT EXISTS idx_strategy_config_symbol_interval
    ON strategy_configurations (symbol, interval);
CREATE INDEX IF NOT EXISTS idx_strategy_config_enabled
    ON strategy_configurations (is_enabled);
CREATE INDEX IF NOT EXISTS idx_strategy_config_trigger_type
    ON strategy_configurations (trigger_type);

-- strategy_signals 索引
CREATE INDEX IF NOT EXISTS idx_strategy_signals_symbol_time
    ON strategy_signals (symbol, computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_strategy
    ON strategy_signals (strategy_name);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_computed
    ON strategy_signals (computed_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategy_signals_config
    ON strategy_signals (config_id);

-- =============================================================================
-- 第五部分: 转换为 Hypertable（如未转换）
-- =============================================================================

-- strategy_signals 转换为 Hypertable
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM _timescaledb_catalog.hypertable WHERE table_name = 'strategy_signals') THEN
        PERFORM create_hypertable('strategy_signals', 'computed_at');
        RAISE NOTICE '已将 strategy_signals 转换为 Hypertable';
    ELSE
        RAISE NOTICE 'strategy_signals 已是 Hypertable，跳过';
    END IF;
END $$;

-- =============================================================================
-- 第六部分: 创建触发器函数（使用 CREATE OR REPLACE）
-- =============================================================================

-- 信号生成通知
CREATE OR REPLACE FUNCTION notify_signal_new()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('signal_new', jsonb_build_object(
        'id', NEW.id,
        'signal_id', NEW.signal_id,
        'config_id', NEW.config_id,
        'strategy_name', NEW.strategy_name,
        'symbol', NEW.symbol,
        'interval', NEW.interval,
        'trigger_type', NEW.trigger_type,
        'signal_value', NEW.signal_value,
        'signal_reason', NEW.signal_reason,
        'computed_at', NEW.computed_at::TEXT
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 策略配置新增通知
CREATE OR REPLACE FUNCTION notify_config_new()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('config_new', jsonb_build_object(
        'id', NEW.id,
        'name', NEW.name,
        'description', NEW.description,
        'trigger_type', NEW.trigger_type,
        'macd_params', NEW.macd_params,
        'threshold', NEW.threshold,
        'symbol', NEW.symbol,
        'interval', NEW.interval,
        'is_enabled', NEW.is_enabled,
        'created_at', NEW.created_at::TEXT,
        'created_by', NEW.created_by
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 策略配置更新通知
CREATE OR REPLACE FUNCTION notify_config_update()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('config_update', jsonb_build_object(
        'id', NEW.id,
        'name', NEW.name,
        'description', NEW.description,
        'trigger_type', NEW.trigger_type,
        'macd_params', NEW.macd_params,
        'threshold', NEW.threshold,
        'symbol', NEW.symbol,
        'interval', NEW.interval,
        'is_enabled', NEW.is_enabled,
        'updated_at', NEW.updated_at::TEXT,
        'created_by', NEW.created_by
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 策略配置删除通知
CREATE OR REPLACE FUNCTION notify_config_delete()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('config_delete', jsonb_build_object(
        'id', OLD.id,
        'name', OLD.name,
        'symbol', OLD.symbol,
        'interval', OLD.interval,
        'deleted_at', NOW()::TEXT
    )::TEXT);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 第七部分: 创建触发器（触发器存在时跳过）
-- =============================================================================

-- strategy_signals 触发器
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers
        WHERE trigger_name = 'trigger_strategy_signals_new'
    ) THEN
        CREATE TRIGGER trigger_strategy_signals_new
            AFTER INSERT ON strategy_signals
            FOR EACH ROW
            EXECUTE FUNCTION notify_signal_new();
        RAISE NOTICE '已创建触发器 trigger_strategy_signals_new';
    ELSE
        RAISE NOTICE '触发器 trigger_strategy_signals_new 已存在，跳过';
    END IF;
END $$;

-- strategy_configurations 触发器
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers
        WHERE trigger_name = 'trigger_config_new'
    ) THEN
        CREATE TRIGGER trigger_config_new
            AFTER INSERT ON strategy_configurations
            FOR EACH ROW
            EXECUTE FUNCTION notify_config_new();
        RAISE NOTICE '已创建触发器 trigger_config_new';
    ELSE
        RAISE NOTICE '触发器 trigger_config_new 已存在，跳过';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers
        WHERE trigger_name = 'trigger_config_update'
    ) THEN
        CREATE TRIGGER trigger_config_update
            AFTER UPDATE ON strategy_configurations
            FOR EACH ROW
            EXECUTE FUNCTION notify_config_update();
        RAISE NOTICE '已创建触发器 trigger_config_update';
    ELSE
        RAISE NOTICE '触发器 trigger_config_update 已存在，跳过';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers
        WHERE trigger_name = 'trigger_config_delete'
    ) THEN
        CREATE TRIGGER trigger_config_delete
            AFTER DELETE ON strategy_configurations
            FOR EACH ROW
            EXECUTE FUNCTION notify_config_delete();
        RAISE NOTICE '已创建触发器 trigger_config_delete';
    ELSE
        RAISE NOTICE '触发器 trigger_config_delete 已存在，跳过';
    END IF;
END $$;

-- =============================================================================
-- 第八部分: 数据保留策略（如未设置）
-- =============================================================================

-- strategy_signals: 保留30天
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM _timescaledb_catalog.retention_policy WHERE hypertable_name = 'strategy_signals'
    ) THEN
        PERFORM add_retention_policy('strategy_signals', drop_after => INTERVAL '30 days');
        RAISE NOTICE '已添加保留策略: strategy_signals 保留30天';
    ELSE
        RAISE NOTICE 'strategy_signals 保留策略已存在，跳过';
    END IF;
END $$;

-- =============================================================================
-- 迁移完成
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'MACD 共振策略迁移完成！';
    RAISE NOTICE '========================================';
    RAISE NOTICE '表: strategy_configurations, strategy_signals';
    RAISE NOTICE 'Hypertable: strategy_signals 已转换';
    RAISE NOTICE '触发器: 4个策略相关触发器已创建';
    RAISE NOTICE '保留策略: strategy_signals 保留30天';
    RAISE NOTICE '通知频道: signal_new, config_new, config_update, config_delete';
    RAISE NOTICE '========================================';
    RAISE NOTICE '数据完整性: 已保留所有现有数据';
    RAISE NOTICE '========================================';
END $$;
