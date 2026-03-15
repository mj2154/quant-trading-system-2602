-- =============================================================================
-- 迁移: 为 strategy_signals 表添加 created_by 字段
--
-- 此迁移确保 strategy_signals 表包含 created_by 字段，与设计文档保持一致
-- =============================================================================

-- 检查字段是否存在，如果不存在则添加
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'strategy_signals' AND column_name = 'created_by'
    ) THEN
        ALTER TABLE strategy_signals ADD COLUMN created_by VARCHAR(100);
        RAISE NOTICE '已为 strategy_signals 表添加 created_by 字段';
    ELSE
        RAISE NOTICE 'strategy_signals.created_by 字段已存在，跳过';
    END IF;
END $$;

-- 为 created_by 字段添加索引（用于按用户查询信号）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_signals_created_by'
    ) THEN
        CREATE INDEX idx_signals_created_by ON strategy_signals (created_by);
        RAISE NOTICE '已创建 idx_signals_created_by 索引';
    ELSE
        RAISE NOTICE '索引 idx_signals_created_by 已存在，跳过';
    END IF;
END $$;

-- 检查并添加复合索引（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_signals_user_strategy_time'
    ) THEN
        CREATE INDEX idx_signals_user_strategy_time
            ON strategy_signals (created_by, strategy_type, computed_at DESC);
        RAISE NOTICE '已创建 idx_signals_user_strategy_time 索引';
    ELSE
        RAISE NOTICE '索引 idx_signals_user_strategy_time 已存在，跳过';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_signals_user_symbol_time'
    ) THEN
        CREATE INDEX idx_signals_user_symbol_time
            ON strategy_signals (created_by, symbol, computed_at DESC);
        RAISE NOTICE '已创建 idx_signals_user_symbol_time 索引';
    ELSE
        RAISE NOTICE '索引 idx_signals_user_symbol_time 已存在，跳过';
    END IF;
END $$;

DO $$
BEGIN
    RAISE NOTICE 'strategy_signals 表迁移完成';
END $$;
