-- =============================================================================
-- 迁移: 重命名 alert_configs 表索引以匹配设计文档
--
-- 文档是唯一真相来源，此迁移将数据库索引重命名为文档中的命名
-- =============================================================================

-- 重命名索引 (使用 IF EXISTS 检查)
-- idx_alerts_user_strategy -> idx_alert_configs_user_strategy
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_alerts_user_strategy') THEN
        ALTER INDEX idx_alerts_user_strategy RENAME TO idx_alert_configs_user_strategy;
        RAISE NOTICE '重命名索引: idx_alerts_user_strategy -> idx_alert_configs_user_strategy';
    END IF;
END $$;

-- idx_alerts_user_symbol -> idx_alert_configs_user_symbol
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_alerts_user_symbol') THEN
        ALTER INDEX idx_alerts_user_symbol RENAME TO idx_alert_configs_user_symbol;
        RAISE NOTICE '重命名索引: idx_alerts_user_symbol -> idx_alert_configs_user_symbol';
    END IF;
END $$;

-- idx_alerts_strategy_symbol -> idx_alert_configs_strategy_symbol
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_alerts_strategy_symbol') THEN
        ALTER INDEX idx_alerts_strategy_symbol RENAME TO idx_alert_configs_strategy_symbol;
        RAISE NOTICE '重命名索引: idx_alerts_strategy_symbol -> idx_alert_configs_strategy_symbol';
    END IF;
END $$;

-- idx_alerts_params_gin -> idx_alert_configs_params_gin
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_alerts_params_gin') THEN
        ALTER INDEX idx_alerts_params_gin RENAME TO idx_alert_configs_params_gin;
        RAISE NOTICE '重命名索引: idx_alerts_params_gin -> idx_alert_configs_params_gin';
    END IF;
END $$;

-- idx_alerts_enabled -> idx_alert_configs_enabled
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_alerts_enabled') THEN
        ALTER INDEX idx_alerts_enabled RENAME TO idx_alert_configs_enabled;
        RAISE NOTICE '重命名索引: idx_alerts_enabled -> idx_alert_configs_enabled';
    END IF;
END $$;

DO $$
BEGIN
    RAISE NOTICE 'alert_configs 索引重命名迁移完成';
END $$;
