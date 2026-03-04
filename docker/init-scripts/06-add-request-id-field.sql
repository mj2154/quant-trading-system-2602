-- -----------------------------------------------------------------------------
-- 迁移: 添加 request_id 顶层字段
--
-- 目的: 将 request_id 从 payload JSON 中提升到顶层字段
-- 原因:
--   1. 贯穿整个数据流: 前端 → API → 币安 → 结果推送
--   2. 可建索引优化查询
--   3. 语义更清晰
--
-- 影响表:
--   - tasks: 添加 request_id 字段和索引
--   - order_tasks: 添加 request_id 字段和索引
--
-- 执行方式:
--   psql -U dbuser -d trading_db -f 06-add-request-id-field.sql
--
-- 参考文档: docs/backend/design/04-trading-orders.md
-- -----------------------------------------------------------------------------

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. tasks 表添加 request_id 字段
-- -----------------------------------------------------------------------------

-- 添加 request_id 字段
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS request_id VARCHAR(50);

-- 从 payload 中提取现有的 requestId 到顶层字段
UPDATE tasks
SET request_id = payload->>'requestId'
WHERE payload ? 'requestId' AND request_id IS NULL;

-- 添加索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_tasks_request_id ON tasks (request_id);

-- -----------------------------------------------------------------------------
-- 2. order_tasks 表添加 request_id 字段
-- -----------------------------------------------------------------------------

-- 添加 request_id 字段
ALTER TABLE order_tasks ADD COLUMN IF NOT EXISTS request_id VARCHAR(50);

-- 从 payload 中提取现有的 requestId 到顶层字段
UPDATE order_tasks
SET request_id = payload->>'requestId'
WHERE payload ? 'requestId' AND request_id IS NULL;

-- 添加索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_order_tasks_request_id ON order_tasks (request_id);

-- -----------------------------------------------------------------------------
-- 3. 验证
-- -----------------------------------------------------------------------------

-- 验证 tasks 表
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tasks' AND column_name = 'request_id'
    ) THEN
        RAISE NOTICE 'tasks 表 request_id 字段添加成功';
    ELSE
        RAISE EXCEPTION 'tasks 表 request_id 字段添加失败';
    END IF;
END $$;

-- 验证 order_tasks 表
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'order_tasks' AND column_name = 'request_id'
    ) THEN
        RAISE NOTICE 'order_tasks 表 request_id 字段添加成功';
    ELSE
        RAISE EXCEPTION 'order_tasks 表 request_id 字段添加失败';
    END IF;
END $$;

COMMIT;

-- -----------------------------------------------------------------------------
-- 完成
-- -----------------------------------------------------------------------------
