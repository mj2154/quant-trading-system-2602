-- =============================================================================
-- 修复 notify_task_completed 触发器
-- 问题: 触发器函数缺少 payload 和 result 字段
-- 修复: 添加缺失的字段以符合设计文档
-- =============================================================================

-- 重新创建 notify_task_completed 函数（添加 payload 和 result 字段）
CREATE OR REPLACE FUNCTION notify_task_completed()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('task_completed', jsonb_build_object(
        'id', NEW.id,
        'type', NEW.type,
        'payload', NEW.payload,
        'result', NEW.result,
        'status', NEW.status,
        'updated_at', NEW.updated_at::TEXT
    )::TEXT);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 验证修复结果
SELECT tgname, pg_get_triggerdef(t.oid) AS trigger_definition
FROM pg_trigger t
WHERE tgname = 'trigger_task_completed';

DO $$
BEGIN
    RAISE NOTICE '修复完成！notify_task_completed 触发器已更新。';
    RAISE NOTICE '现在通知将包含 payload 和 result 字段。';
END $$;
