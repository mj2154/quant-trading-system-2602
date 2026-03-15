-- 09-add-name-to-signals.sql
-- 为 strategy_signals 表添加 name 字段（冗余存储告警名称）
-- 设计文档: docs/backend/design/07-websocket-protocol.md

-- 添加 name 字段
ALTER TABLE strategy_signals
ADD COLUMN IF NOT EXISTS name VARCHAR(100) NOT NULL DEFAULT 'Unknown';

-- 更新已有的记录：从 alert_configs 表关联获取 name
UPDATE strategy_signals s
SET name = COALESCE(
    (SELECT a.name FROM alert_configs a WHERE a.id = s.alert_id),
    'Unknown'
)
WHERE s.name = 'Unknown';

-- 更新 notify_signal_new 触发器（包含 name 字段）
CREATE OR REPLACE FUNCTION notify_signal_new()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('signal_new', jsonb_build_object(
        'event_id', uuidv7()::TEXT,
        'event_type', 'signal_new',
        'timestamp', NOW()::TEXT,
        'data', jsonb_build_object(
            'id', NEW.id,
            'alert_id', NEW.alert_id,
            'name', NEW.name,
            'created_by', NEW.created_by,
            'strategy_type', NEW.strategy_type,
            'symbol', NEW.symbol,
            'interval', NEW.interval,
            'trigger_type', NEW.trigger_type,
            'signal_value', NEW.signal_value,
            'signal_reason', NEW.signal_reason,
            'computed_at', NEW.computed_at::TEXT,
            'source_subscription_key', NEW.source_subscription_key
        )
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 验证字段已添加
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'strategy_signals' AND column_name = 'name';
