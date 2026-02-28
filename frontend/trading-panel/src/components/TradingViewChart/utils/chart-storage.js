/**
 * TradingView 图表本地存储适配器
 * 实现 IExternalSaveLoadAdapter 接口，支持图表保存/加载功能
 */

const STORAGE_KEYS = {
    CHARTS: 'tradingview_charts',
    LAST_CHART_ID: 'tradingview_last_chart_id',
    SETTINGS: 'tradingview_settings'
};

/**
 * 生成唯一图表 ID
 */
function generateChartId() {
    return `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 生成默认图表名称
 */
function generateDefaultChartName() {
    const now = new Date();
    const dateStr = now.toISOString().split('T')[0];
    const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '-');
    return `图表 ${dateStr} ${timeStr}`;
}

/**
 * 从 localStorage 获取数据
 */
function getFromStorage(key, defaultValue = []) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : defaultValue;
    } catch (error) {
        return defaultValue;
    }
}

/**
 * 保存数据到 localStorage
 */
function saveToStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (error) {
        return false;
    }
}

/**
 * TradingView 图表存储适配器
 * 符合 IExternalSaveLoadAdapter 接口规范
 */
export const chartStorageAdapter = {
    /**
     * 保存图表
     * @param {Object} chartData - 图表数据（符合 ChartData 接口）
     * @returns {Promise<string|number>} 图表 ID
     */
    async saveChart(chartData) {
        try {
            // 验证必需字段（符合 ChartData 接口要求）
            if (!chartData || typeof chartData !== 'object') {
                return null;
            }

            // 如果没有提供名称，生成默认名称
            if (!chartData.name || typeof chartData.name !== 'string' || chartData.name.trim() === '') {
                chartData.name = generateDefaultChartName();
            }

            if (!chartData.symbol || typeof chartData.symbol !== 'string') {
                return null;
            }

            if (!chartData.resolution || typeof chartData.resolution !== 'string') {
                return null;
            }

            if (!chartData.content || typeof chartData.content !== 'string') {
                return null;
            }

            const charts = getFromStorage(STORAGE_KEYS.CHARTS, []);
            const chartId = chartData.id || generateChartId();

            const chartInfo = {
                id: chartId,
                name: chartData.name,
                symbol: chartData.symbol,
                resolution: chartData.resolution,
                timestamp: Date.now(),
                data: chartData
            };

            // 检查是否已存在同名图表
            const existingIndex = charts.findIndex(c => c.name === chartInfo.name);
            if (existingIndex !== -1) {
                charts[existingIndex] = chartInfo;
            } else {
                charts.push(chartInfo);
            }

            // 按时间戳降序排列（最新的在前）
            charts.sort((a, b) => b.timestamp - a.timestamp);

            // 限制存储数量（保留最近 20 个图表）
            if (charts.length > 20) {
                charts.splice(20);
            }

            const success = saveToStorage(STORAGE_KEYS.CHARTS, charts);

            if (success) {
                saveToStorage(STORAGE_KEYS.LAST_CHART_ID, chartId);
                return chartId;
            }
            return null;
        } catch (error) {
            return null;
        }
    },

    /**
     * 加载图表内容
     * @param {string|number} chartId - 图表 ID
     * @returns {Promise<string>} 图表内容（chart.content 字段）
     */
    async getChartContent(chartId) {
        try {
            const charts = getFromStorage(STORAGE_KEYS.CHARTS, []);
            const chart = charts.find(c => c.id === chartId);

            if (chart && chart.data && chart.data.content) {
                return chart.data.content;
            }
            return null;
        } catch (error) {
            return null;
        }
    },

    /**
     * 删除图表
     * @param {string|number} chartId - 图表 ID
     * @returns {Promise<void>}
     */
    async removeChart(chartId) {
        try {
            const charts = getFromStorage(STORAGE_KEYS.CHARTS, []);
            const index = charts.findIndex(c => c.id === chartId);

            if (index !== -1) {
                charts.splice(index, 1);
                saveToStorage(STORAGE_KEYS.CHARTS, charts);
            }
        } catch (error) {
        }
    },

    /**
     * 获取所有图表列表
     * @returns {Promise<Array>} 图表元信息列表
     */
    async getAllCharts() {
        try {
            const charts = getFromStorage(STORAGE_KEYS.CHARTS, []);

            // 返回完整的图表元信息（符合 ChartMetaInfo 接口）
            const chartList = charts.map(chart => ({
                id: chart.id,
                name: chart.name,
                symbol: chart.data?.symbol || 'BINANCE:BTCUSDT',
                resolution: chart.data?.resolution || '60',
                timestamp: chart.timestamp
            }));

            return chartList;
        } catch (error) {
            return [];
        }
    },

    /**
     * 获取最后使用的图表 ID
     */
    getLastChartId() {
        try {
            return localStorage.getItem(STORAGE_KEYS.LAST_CHART_ID);
        } catch (error) {
            return null;
        }
    },

    /**
     * 清除所有图表数据（调试用）
     */
    clearAllCharts() {
        try {
            localStorage.removeItem(STORAGE_KEYS.CHARTS);
            localStorage.removeItem(STORAGE_KEYS.LAST_CHART_ID);
        } catch (error) {
        }
    },

    // ==================== 图表模板相关方法 ====================

    /**
     * 获取所有图表模板名称
     * @returns {Promise<string[]>}
     */
    async getAllChartTemplates() {
        return [];
    },

    async saveChartTemplate(templateName, content) {
        return Promise.resolve();
    },

    async removeChartTemplate(templateName) {
        return Promise.resolve();
    },

    async getChartTemplateContent(templateName) {
        return {};
    },

    async getAllStudyTemplates() {
        return [];
    },

    async saveStudyTemplate(studyTemplateData) {
        return Promise.resolve();
    },

    async removeStudyTemplate(studyTemplateInfo) {
        return Promise.resolve();
    },

    async getStudyTemplateContent(studyTemplateInfo) {
        return '';
    },

    async getDrawingTemplates(toolName) {
        return [];
    },

    async saveDrawingTemplate(toolName, templateName, content) {
        return Promise.resolve();
    },

    async loadDrawingTemplate(toolName, templateName) {
        return '';
    },

    async removeDrawingTemplate(toolName, templateName) {
        return Promise.resolve();
    }
};
