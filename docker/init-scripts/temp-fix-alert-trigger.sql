-- 临时修复脚本：修正 alert_config 触发器的时间格式和缺失字段
-- 执行：docker exec -it timescale-db psql -U dbuser -d trading_db -f /docker-entrypoint-initdb.d/temp-fix-alert-trigger.sql
-- 时间：2026-03-26

-- ============================================================================
-- 1. 重建 alert_config 新增通知函数（INSERT 触发器）
-- ============================================================================
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
                'created_at', TO_CHAR(NEW.created_at, 'YYYY-MM-DD"T"HH24:MI:SS.FF6TZH:TZM')
            )
        )::TEXT);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 重新创建触发器（确保使用新函数）
DROP TRIGGER IF EXISTS trigger_alert_config_new ON alert_configs;
CREATE TRIGGER trigger_alert_config_new
    AFTER INSERT ON alert_configs
    FOR EACH ROW
    EXECUTE FUNCTION notify_alert_config_new();

-- ============================================================================
-- 2. 重建 alert_config 更新通知函数（UPDATE 触发器）
-- 修复：添加缺失的 created_at 字段，使用 ISO 8601 时间格式
-- ============================================================================
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
            'created_at', TO_CHAR(NEW.created_at, 'YYYY-MM-DD"T"HH24:MI:SS.FF6TZH:TZM'),
            'updated_at', TO_CHAR(NEW.updated_at, 'YYYY-MM-DD"T"HH24:MI:SS.FF6TZH:TZM'),
            'created_by', NEW.created_by
        )
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 重新创建触发器（确保使用新函数）
DROP TRIGGER IF EXISTS trigger_alert_config_update ON alert_configs;
CREATE TRIGGER trigger_alert_config_update
    AFTER UPDATE ON alert_configs
    FOR EACH ROW
    EXECUTE FUNCTION notify_alert_config_update();

-- ============================================================================
-- 验证：查询触发器状态
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'alert_config 触发器修复完成';
    RAISE NOTICE 'trigger_alert_config_new: 已重建';
    RAISE NOTICE 'trigger_alert_config_update: 已重建（已添加 created_at，修正时间格式）';
    RAISE NOTICE '========================================';
END $$;
