-- =============================================================================
-- 历史K线数据格式迁移脚本
-- 将币安格式转换为TV格式
--
-- 格式对照表:
-- 币安格式  -> TV格式
-- 1m        -> 1
-- 3m        -> 3
-- 5m        -> 5
-- 15m       -> 15
-- 30m       -> 30
-- 1h        -> 60
-- 2h        -> 120
-- 4h        -> 240
-- 6h        -> 360
-- 12h       -> 720
-- 1d        -> D
-- 3d        -> 3D
-- 1w        -> W
-- 1M        -> M
-- =============================================================================

-- 1. 先备份当前数据（可选）
-- CREATE TABLE klines_history_backup AS SELECT * FROM klines_history;

-- 2. 执行批量转换
UPDATE klines_history SET interval = '1'  WHERE interval = '1m';
UPDATE klines_history SET interval = '3'  WHERE interval = '3m';
UPDATE klines_history SET interval = '5'  WHERE interval = '5m';
UPDATE klines_history SET interval = '15' WHERE interval = '15m';
UPDATE klines_history SET interval = '30' WHERE interval = '30m';
UPDATE klines_history SET interval = '60' WHERE interval = '1h';
UPDATE klines_history SET interval = '120' WHERE interval = '2h';
UPDATE klines_history SET interval = '240' WHERE interval = '4h';
UPDATE klines_history SET interval = '360' WHERE interval = '6h';
UPDATE klines_history SET interval = '720' WHERE interval = '12h';
UPDATE klines_history SET interval = 'D'   WHERE interval = '1d';
UPDATE klines_history SET interval = '3D' WHERE interval = '3d';
UPDATE klines_history SET interval = 'W'   WHERE interval = '1w';
UPDATE klines_history SET interval = 'M'   WHERE interval = '1M';

-- 3. realtime_data 表无需处理（interval 存储在 JSONB 的 data 字段中）
--    新写入的数据已通过 binance_service.py 的转换函数自动转换

-- 4. 验证转换结果
SELECT DISTINCT interval FROM klines_history ORDER BY interval;
