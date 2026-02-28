#!/bin/bash
# =============================================================================
# 数据库迁移清理脚本
# 修复迁移过程中的问题
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo ""
echo "========================================"
echo "数据库迁移清理工具"
echo "========================================"
echo ""

# 停止服务
log_step "停止服务..."
docker-compose stop api-service binance-service 2>/dev/null || true
log_info "服务已停止"

# 1. 删除旧表
log_step "删除旧表..."
docker exec -i timescale-db psql -U dbuser -d trading_db << 'EOF'
-- 删除旧表
DROP TABLE IF EXISTS klines_live CASCADE;
DROP TABLE IF EXISTS subscription_keys CASCADE;
DROP TABLE IF EXISTS task_results CASCADE;

-- 删除旧触发器函数（如果存在）
DROP FUNCTION IF EXISTS notify_kline_new() CASCADE;
DROP FUNCTION IF EXISTS notify_kline_closed() CASCADE;
DROP FUNCTION IF EXISTS notify_realtime_data() CASCADE;
DROP FUNCTION IF EXISTS notify_subscription_change() CASCADE;

-- 删除旧的触发器
DROP TRIGGER IF EXISTS trigger_kline_closed ON klines_live CASCADE;
DROP TRIGGER IF EXISTS trigger_kline_closed_update ON klines_live CASCADE;
DROP TRIGGER IF EXISTS trigger_kline_new ON klines_live CASCADE;
DROP TRIGGER IF EXISTS trigger_kline_update ON klines_live CASCADE;

-- 删除旧索引
DROP INDEX IF EXISTS idx_rt_data_type CASCADE;
DROP INDEX IF EXISTS idx_rt_symbol CASCADE;
DROP INDEX IF EXISTS idx_rt_exchange CASCADE;
DROP INDEX IF EXISTS idx_rt_updated CASCADE;
DROP INDEX IF EXISTS idx_sub_keys_key CASCADE;

\log_info "旧表和触发器已清理"
EOF

# 2. 修复 klines_history 表结构
log_step "修复 klines_history 表结构..."

# 先备份旧数据
docker exec -i timescale-db psql -U dbuser -d trading_db << 'EOF'
-- 创建临时表保存旧数据
CREATE TEMP TABLE klines_history_old AS SELECT * FROM klines_history;

\log_info "旧 klines_history 数据已备份到临时表"
EOF

# 删除旧表并创建新表
docker exec -i timescale-db psql -U dbuser -d trading_db << 'EOF'
-- 删除旧表
DROP TABLE IF EXISTS klines_history CASCADE;

-- 创建新的 klines_history 表（JSON格式）
CREATE TABLE klines_history (
    id BIGSERIAL PRIMARY KEY,
    subscription_key VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,
    event_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT klines_history_unique
        UNIQUE (subscription_key, (data->>'open_time'))
);

SELECT create_hypertable('klines_history', 'created_at');
CREATE INDEX IF NOT EXISTS idx_klines_history_subscription_time
    ON klines_history (subscription_key, (data->>'open_time') DESC);

\log_info "新 klines_history 表已创建"
EOF

# 3. 恢复数据（如果有的话）
log_step "恢复 klines_history 数据..."
docker exec -i timescale-db psql -U dbuser -d trading_db << 'EOF'
-- 从备份恢复数据（转换为新格式）
INSERT INTO klines_history (subscription_key, data, event_time)
SELECT
    'BINANCE:' || symbol || '@KLINE_' || interval AS subscription_key,
    jsonb_build_object(
        'symbol', symbol,
        'interval', interval,
        'open_time', open_time,
        'close_time', close_time,
        'open_price', open_price,
        'high_price', high_price,
        'low_price', low_price,
        'close_price', close_price,
        'volume', volume,
        'quote_volume', quote_volume,
        'number_of_trades', number_of_trades,
        'taker_buy_base_volume', taker_buy_base_volume,
        'taker_buy_quote_volume', taker_buy_quote_volume,
        'is_closed', true
    ) AS data,
    close_time AS event_time
FROM klines_history_old;

\log_info 'klines_history 数据已恢复到新格式'
EOF

# 4. 创建缺失的触发器
log_step "创建缺失的触发器..."
docker exec -i timescale-db psql -U dbuser -d trading_db << 'EOF'
-- 创建缺失的 subscription_clean 触发器
CREATE OR REPLACE FUNCTION notify_subscription_clean()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('subscription_clean', jsonb_build_object(
        'action', 'clean_all',
        'timestamp', NOW()::TEXT
    )::TEXT);
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
DROP TRIGGER IF EXISTS trigger_realtime_data_clean ON realtime_data;
CREATE TRIGGER trigger_realtime_data_clean
    AFTER TRUNCATE ON realtime_data
    FOR EACH STATEMENT
    EXECUTE FUNCTION notify_subscription_clean();

\log_info "缺失的触发器已创建"
EOF

# 5. 设置保留策略
log_step "设置数据保留策略..."
docker exec -i timescale-db psql -U dbuser -d trading_db << 'EOF'
-- 删除旧策略
SELECT remove_retention_policy('tasks', if_exists => true);
SELECT remove_retention_policy('realtime_data', if_exists => true);
SELECT remove_retention_policy('klines_history', if_exists => true);

-- 添加新策略
SELECT add_retention_policy('tasks', INTERVAL '7 days');
SELECT add_retention_policy('realtime_data', INTERVAL '1 day');
SELECT add_retention_policy('klines_history', INTERVAL '1 year');

\log_info "保留策略已设置"
EOF

# 6. 验证结果
log_step "验证迁移结果..."
docker exec -i timescale-db psql -U dbuser -d trading_db << 'EOF'
-- 检查表
SELECT 'Tables:' as info;
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

-- 检查触发器
SELECT '' as '';
SELECT 'Triggers:' as info;
SELECT trigger_name, event_object_table, action_timing
FROM information_schema.triggers
WHERE event_object_schema = 'public'
ORDER BY event_object_table, trigger_name;

-- 检查数据
SELECT '' as '';
SELECT 'Data Counts:' as info;
SELECT 'klines_history' as table_name, COUNT(*) as row_count FROM klines_history
UNION ALL
SELECT 'realtime_data' as table_name, COUNT(*) as row_count FROM realtime_data
UNION ALL
SELECT 'tasks' as table_name, COUNT(*) as row_count FROM tasks
UNION ALL
SELECT 'exchange_info' as table_name, COUNT(*) as row_count FROM exchange_info;
EOF

# 重启服务
log_step "重启服务..."
docker-compose start api-service binance-service
log_info "服务已重启"

echo ""
echo "========================================"
log_info "清理完成！"
echo "========================================"
echo ""
