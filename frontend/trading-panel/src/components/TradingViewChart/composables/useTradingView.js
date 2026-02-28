/**
 * TradingView 图表管理 Composable
 * 负责初始化、管理和清理 TradingView Widget
 */

import { ref, onBeforeUnmount } from 'vue';
import { getCustomIndicators } from '../utils/custom-indicators.js';
import Datafeed from '../utils/datafeed.js';
import { chartStorageAdapter } from '../utils/chart-storage.js';

/**
 * 使用 TradingView 图表
 * @param {string} containerId - DOM 容器 ID（默认: 'tv_chart_container'）
 * @returns {Object} TradingView 管理 API
 */
export function useTradingView(containerId = 'tv_chart_container') {
    // Widget 实例引用
    const widget = ref(null);
    const isReady = ref(false);
    const isLoading = ref(false);
    const error = ref(null);


    /**
     * 创建 TradingView Widget
     */
    const createWidget = () => {
        if (isLoading.value || isReady.value) {
            return;
        }

        isLoading.value = true;
        error.value = null;

        try {
            // 创建 Widget
            widget.value = new TradingView.widget({
                container: containerId,
                datafeed: Datafeed,
                library_path: '../../src/components/TradingViewChart/library/',
                locale: 'zh',
                theme: 'dark', // 设置暗夜主题
                symbol: 'BINANCE:BTCUSDT', // ✅ 保留：作为默认symbol（会被保存的图表覆盖）
                interval: '60',
                autosize: true,

                // ✅ 添加：使用本地存储适配器
                save_load_adapter: chartStorageAdapter,

                // ✅ 添加：自动加载最近使用的图表
                load_last_chart: true,

                // 禁用本地存储缓存 + 隐藏左侧绘图工具栏 + 隐藏默认交易量指标 + 关闭账户管理器
                disabled_features: [
                    "left_toolbar",
                    "create_volume_indicator_by_default",
                    "use_localstorage_for_settings",
                    "trading_account_manager"
                ],

                // 启用图表模板存储功能 + 显示保存/加载布局按钮
                enabled_features: [
                    "chart_template_storage",
                    "header_saveload"
                ],

                widgetbar: {
                    watchlist: true,
                    watchlist_settings: {
                        default_symbols: [
                            "BINANCE:BTCUSDT",
                            "BINANCE:ETHUSDT",
                            "BINANCE:LTCUSDT",
                            "BINANCE:XRPUSDT",
                            "BINANCE:BNBUSDT"
                        ],
                        readonly: false  // 允许交互
                    }
                },
                // 自定义指标
                custom_indicators_getter: function(PineJS) {
                    return getCustomIndicators(PineJS);
                }
            });

            // 监听图表就绪事件
            widget.value.onChartReady(() => {
                isReady.value = true;
                isLoading.value = false;

                // 设置图表API引用（用于WebSocket重连时调用 resetCache/resetData）
                Datafeed.setChartApi(widget.value);

                // 强制应用暗色主题（防止用户设置覆盖）
                widget.value.changeTheme("dark");

                // 延迟再次应用主题，确保覆盖用户设置
                setTimeout(() => {
                    widget.value.changeTheme("dark");
                }, 100);

                // 获取图表实例
                const chart = widget.value.activeChart();

                // 订阅分辨率变化事件（用于数据刷新）
                chart.onIntervalChanged().subscribe(null, () => {
                    widget.value.resetCache();
                    chart.resetData();
                });

                // ✅ 移除：不再自动加载默认技术指标
                // 让用户自己添加和保存技术指标
            });

        } catch (err) {
            error.value = err;
            isLoading.value = false;
        }
    };

    /**
     * 销毁 Widget
     */
    const destroyWidget = () => {
        if (widget.value) {
            try {
                widget.value.remove();
                widget.value = null;
                isReady.value = false;
            } catch (err) {
                // 静默处理销毁错误
            }
        }

    };

    /**
     * 重新加载图表
     */
    const reload = () => {
        destroyWidget();
        createWidget();
    };

    /**
     * 获取 Widget 实例
     * @returns {Object|null} TradingView Widget 实例
     */
    const getWidget = () => {
        return widget.value;
    };

    /**
     * 获取图表实例
     * @returns {Object|null} 图表实例
     */
    const getChart = () => {
        if (widget.value && isReady.value) {
            return widget.value.activeChart();
        }
        return null;
    };

    // 组件卸载时清理资源
    onBeforeUnmount(() => {
        destroyWidget();
    });

    return {
        widget,
        isReady,
        isLoading,
        error,
        createWidget,
        destroyWidget,
        reload,
        getWidget,
        getChart
    };
}
