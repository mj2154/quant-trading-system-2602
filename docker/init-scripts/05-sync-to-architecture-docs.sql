-- =============================================================================
-- 数据库迁移脚本：将数据库现状同步至文档设计
-- 执行顺序：05-sync-to-architecture-docs.sql
-- 文档版本：QUANT_TRADING_SYSTEM_ARCHITECTURE.md
--
-- 迁移内容：
-- 1. 重命名 alert_signals → alert_configs
-- 2. 创建 notify_alert_config_* 函数
-- 3. 删除遗留的 strategy_configurations 表
-- 4. 更新 strategy_signals 表结构（删除多余字段）
-- 5. 更新触发器使用新的通知频道
-- =============================================================================

BEGIN;

-- =============================================================================
-- 1. 重命名 alert_signals 为 alert_configs（以文档为准）
-- =============================================================================

-- 由于 alert_signals 为空，直接重命名即可
ALTER TABLE IF EXISTS alert_signals RENAME TO alert_configs;

-- 更新索引名称（保持一致性）
ALTER INDEX IF EXISTS idx_alerts_enabled RENAME TO idx_alert_configs_enabled;
ALTER INDEX IF EXISTS idx_alerts_params_gin RENAME TO idx_alert_configs_params_gin;
ALTER INDEX IF EXISTS idx_alerts_strategy_symbol RENAME TO idx_alert_configs_strategy_symbol;
ALTER INDEX IF EXISTS idx_alerts_user_strategy RENAME TO idx_alert_configs_user_strategy;
ALTER INDEX IF EXISTS idx_alerts_user_symbol RENAME TO idx_alert_configs_user_symbol;

-- =============================================================================
-- 2. 创建 alert_configs 触发器函数（以文档为准）
-- =============================================================================

-- notify_alert_config_new: 告警配置新增时通知
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

-- notify_alert_config_update: 告警配置更新时通知
CREATE OR REPLACE FUNCTION notify_alert_config_update()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_enabled != NEW.is_enabled OR NEW.is_enabled = TRUE THEN
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
                'created_by', NEW.created_by,
                'updated_at', NEW.updated_at::TEXT
            )
        )::TEXT);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- notify_alert_config_delete: 告警配置删除时通知
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
            'created_by', OLD.created_by
        )
    )::TEXT);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 3. 更新 alert_configs 触发器
-- =============================================================================

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

-- 删除旧的 alert_signals 触发器（已不存在）
DROP TRIGGER IF EXISTS trigger_alert_signal_new ON alert_signals;
DROP TRIGGER IF EXISTS trigger_alert_signal_update ON alert_signals;
DROP TRIGGER IF EXISTS trigger_alert_signal_delete ON alert_signals;

-- =============================================================================
-- 4. 删除遗留的 strategy_configurations 表（文档中未定义）
-- =============================================================================

DROP TRIGGER IF EXISTS trigger_config_delete ON strategy_configurations;
DROP TRIGGER IF EXISTS trigger_config_new ON strategy_configurations;
DROP TRIGGER IF EXISTS trigger_config_update ON strategy_configurations;

DROP TABLE IF EXISTS strategy_configurations CASCADE;

-- =============================================================================
-- 5. 更新 strategy_signals 表结构（以文档为准，删除多余字段）
-- =============================================================================

-- 删除多余字段：signal_reason, kline_snapshot, params_snapshot
ALTER TABLE strategy_signals DROP COLUMN IF EXISTS signal_reason;
ALTER TABLE strategy_signals DROP COLUMN IF EXISTS kline_snapshot;
ALTER TABLE strategy_signals DROP COLUMN IF EXISTS params_snapshot;

-- 删除多余索引
DROP INDEX IF EXISTS idx_signals_params_gin;

-- =============================================================================
-- 6. 更新 strategy_signals 触发器函数（统一通知格式）
-- =============================================================================

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
            'computed_at', NEW.computed_at::TEXT,
            'source_subscription_key', NEW.source_subscription_key,
            'metadata', NEW.metadata
        )
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 7. 更新 tasks 表触发器函数（统一通知格式：使用点号分隔）
-- =============================================================================

-- notify_task_new: 任务创建通知
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

-- notify_task_completed: 任务完成通知
CREATE OR REPLACE FUNCTION notify_task_completed()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('task.completed', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'task.completed',
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

-- =============================================================================
-- 8. 更新 realtime_data 触发器函数（统一通知格式：使用点号分隔）
-- =============================================================================

-- notify_realtime_update: 实时数据更新通知
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

-- notify_subscription_add: 订阅新增通知
CREATE OR REPLACE FUNCTION notify_subscription_add()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('subscription.add', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'subscription.add',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'subscription_key', NEW.subscription_key,
            'data_type', NEW.data_type,
            'subscribers', NEW.subscribers
        )
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- notify_subscription_remove: 订阅删除通知
CREATE OR REPLACE FUNCTION notify_subscription_remove()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('subscription.remove', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'subscription.remove',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'subscription_key', OLD.subscription_key,
            'data_type', OLD.data_type
        )
    )::TEXT);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 提交迁移
-- =============================================================================

COMMIT;

-- =============================================================================
-- 验证迁移结果
-- =============================================================================

SELECT 'Tables:' as info;
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
ORDER BY table_name;

SELECT 'Triggers:' as info;
SELECT trigger_name, event_object_table
FROM information_schema.triggers
WHERE trigger_name LIKE 'trigger_%'
ORDER BY event_object_table, trigger_name;

SELECT 'Notify Functions:' as info;
SELECT proname FROM pg_proc
WHERE proname LIKE 'notify_%'
ORDER BY proname;
