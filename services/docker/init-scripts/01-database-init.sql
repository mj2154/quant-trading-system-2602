-- ============================================================================
-- 数据库初始化脚本
-- 单一真相来源：所有表结构、触发器、函数都在此文件中定义
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TimescaleDB 超表创建 (用于时序数据)
-- ----------------------------------------------------------------------------

-- K线时序数据超表
SELECT create_hypertable('klines_live', 'open_time');

-- 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_klines_symbol_interval ON klines_live (symbol, interval DESC, open_time DESC);


-- ----------------------------------------------------------------------------
-- 交易所交易对信息表
-- ----------------------------------------------------------------------------

-- 删除旧表（如果存在）
DROP TABLE IF EXISTS exchange_info CASCADE;

-- 创建交易所交易对信息表
CREATE TABLE exchange_info (
    id                  BIGSERIAL        PRIMARY KEY,

    -- 基本标识
    exchange            VARCHAR(20)      NOT NULL DEFAULT 'BINANCE',
    market_type         VARCHAR(20)      NOT NULL,      -- 'SPOT', 'FUTURES'
    symbol              VARCHAR(50)      NOT NULL,

    -- 基础/报价资产
    base_asset          VARCHAR(20)      NOT NULL,
    quote_asset         VARCHAR(20)      NOT NULL,

    -- 精度信息 (用于下单价格/数量格式化)
    price_precision     INTEGER          NOT NULL DEFAULT 8,
    quantity_precision   INTEGER          NOT NULL DEFAULT 8,

    -- 状态
    status              VARCHAR(20)      NOT NULL DEFAULT 'TRADING',  -- TRADING, HALT, BREAK

    -- 交易规则过滤器 (JSONB存储，币安15+种过滤器类型)
    filters             JSONB            NOT NULL DEFAULT '{}',

    -- 交易选项
    order_types         JSONB,           -- ["LIMIT", "MARKET", "STOP", ...]
    permissions         JSONB,           -- ["SPOT"], ["TRADING"]
    iceberg_allowed     BOOLEAN          DEFAULT FALSE,
    oco_allowed         BOOLEAN          DEFAULT FALSE,

    -- 元数据
    last_updated        TIMESTAMPTZ      DEFAULT NOW(),

    -- 唯一约束
    CONSTRAINT uk_exchange_symbol UNIQUE (exchange, market_type, symbol)
);

-- 完整交易对名称计算列（用于前端显示）
-- 注意：TimescaleDB超表不支持GENERATED列，需要使用触发器或视图
-- 这里我们添加普通列，由应用层或触发器维护
ALTER TABLE exchange_info ADD COLUMN full_symbol VARCHAR(100);

-- 创建更新触发器来维护full_symbol列
CREATE OR REPLACE FUNCTION update_exchange_info_full_symbol()
RETURNS TRIGGER AS $$
BEGIN
    NEW.full_symbol = NEW.exchange || ':' || NEW.symbol ||
        CASE WHEN NEW.market_type = 'FUTURES' THEN '.PERP' ELSE '' END;
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_exchange_info_full_symbol ON exchange_info;
CREATE TRIGGER trigger_exchange_info_full_symbol
    BEFORE INSERT OR UPDATE ON exchange_info
    FOR EACH ROW
    EXECUTE FUNCTION update_exchange_info_full_symbol();

-- 索引
CREATE INDEX IF NOT EXISTS idx_exchange_market ON exchange_info(exchange, market_type);
CREATE INDEX IF NOT EXISTS idx_full_symbol ON exchange_info(full_symbol);
CREATE INDEX IF NOT EXISTS idx_exchange_status ON exchange_info(status);


-- ----------------------------------------------------------------------------
-- 存储过程：Upsert交易所信息
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION upsert_exchange_info(
    p_exchange VARCHAR,
    p_market_type VARCHAR,
    p_symbol VARCHAR,
    p_base_asset VARCHAR,
    p_quote_asset VARCHAR,
    p_price_precision INTEGER,
    p_quantity_precision INTEGER,
    p_status VARCHAR,
    p_filters JSONB,
    p_order_types JSONB,
    p_permissions JSONB,
    p_iceberg_allowed BOOLEAN,
    p_oco_allowed BOOLEAN
) RETURNS BIGINT AS $$
DECLARE
    v_id BIGINT;
BEGIN
    INSERT INTO exchange_info (
        exchange,
        market_type,
        symbol,
        base_asset,
        quote_asset,
        price_precision,
        quantity_precision,
        status,
        filters,
        order_types,
        permissions,
        iceberg_allowed,
        oco_allowed,
        last_updated
    ) VALUES (
        p_exchange,
        p_market_type,
        p_symbol,
        p_base_asset,
        p_quote_asset,
        p_price_precision,
        p_quantity_precision,
        p_status,
        p_filters,
        p_order_types,
        p_permissions,
        p_iceberg_allowed,
        p_oco_allowed,
        NOW()
    )
    ON CONFLICT (exchange, market_type, symbol) DO UPDATE SET
        base_asset = EXCLUDED.base_asset,
        quote_asset = EXCLUDED.quote_asset,
        price_precision = EXCLUDED.price_precision,
        quantity_precision = EXCLUDED.quantity_precision,
        status = EXCLUDED.status,
        filters = EXCLUDED.filters,
        order_types = EXCLUDED.order_types,
        permissions = EXCLUDED.permissions,
        iceberg_allowed = EXCLUDED.iceberg_allowed,
        oco_allowed = EXCLUDED.oco_allowed,
        last_updated = NOW()
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$ LANGUAGE plpgsql;


-- ----------------------------------------------------------------------------
-- 任务队列表 (用于数据库通知机制)
-- ----------------------------------------------------------------------------

DROP TABLE IF EXISTS task_queue CASCADE;

CREATE TABLE task_queue (
    id              BIGSERIAL       PRIMARY KEY,
    task_type       VARCHAR(50)     NOT NULL,
    symbol          VARCHAR(50),
    interval        VARCHAR(10),
    payload         JSONB           NOT NULL DEFAULT '{}',
    status          VARCHAR(20)     NOT NULL DEFAULT 'PENDING',  -- PENDING, PROCESSING, COMPLETED, FAILED
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,
    error_message   TEXT
);

-- 任务索引
CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_queue_type ON task_queue(task_type);


-- ----------------------------------------------------------------------------
-- 数据库通知通道
-- ----------------------------------------------------------------------------

-- PostgreSQL LISTEN/NOTIFY 使用文本频道名
-- 不需要预先创建通道，直接在NOTIFY时指定即可
-- 监听示例: LISTEN task_subscribe; NOTIFY task_subscribe, 'payload';
--
-- 通道列表:
-- - task_subscribe: 任务订阅通道 (binance-service 监听)
-- - kline_new: K线新数据通道 (API服务监听)
-- - signal_new: 信号新数据通道
-- - trade_completed: 交易完成通道


-- ----------------------------------------------------------------------------
-- 触发器：自动通知新任务
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION notify_task_inserted()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('task_subscribe', row_to_json(NEW)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_task_notify ON task_queue;
CREATE TRIGGER trigger_task_notify
    AFTER INSERT ON task_queue
    FOR EACH ROW
    EXECUTE FUNCTION notify_task_inserted();


-- ----------------------------------------------------------------------------
-- 触发器：K线新数据通知
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION notify_kline_inserted()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('kline_new', row_to_json(NEW)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_kline_notify ON klines_live;
CREATE TRIGGER trigger_kline_notify
    AFTER INSERT ON klines_live
    FOR EACH ROW
    WHEN (NEW.is_closed = TRUE)
    EXECUTE FUNCTION notify_kline_inserted();
