/**
 * TradingView 图表主题管理 Composable
 * 负责处理外部主题控制，移除内部主题切换 UI
 */

import { ref, watch, onMounted } from 'vue';

/**
 * 从 localStorage 读取保存的主题设置
 * @returns {string} 'light' 或 'dark'
 */
function getSavedTheme() {
    try {
        return localStorage.getItem('tradingview_theme') || 'light';
    } catch (error) {
        return 'light';
    }
}

/**
 * 保存主题偏好到 localStorage
 * @param {string} theme - 'light' 或 'dark'
 */
function saveTheme(theme) {
    try {
        localStorage.setItem('tradingview_theme', theme);
    } catch (error) {
    }
}

/**
 * 使用主题管理
 * @param {Ref} widgetRef - TradingView Widget 实例的 Ref
 * @param {string|Ref<string>} externalTheme - 外部传入的主题（'light' 或 'dark'）
 * @param {Object} options - 选项
 * @param {boolean} options.persistTheme - 是否持久化主题到 localStorage（默认: true）
 * @returns {Object} 主题管理方法
 */
export function useTheme(widgetRef, externalTheme, options = {}) {
    const {
        persistTheme = true
    } = options;

    // 当前主题状态
    const currentTheme = ref(getSavedTheme());
    const isThemeChanging = ref(false);

    /**
     * 应用主题到 TradingView Widget
     * @param {string} theme - 主题名称 ('light' 或 'dark')
     */
    const applyTheme = async (theme) => {
        const widget = widgetRef.value;

        if (!widget) {
            return;
        }

        if (isThemeChanging.value) {
            return;
        }

        isThemeChanging.value = true;

        try {
            await widget.changeTheme(theme, { disableUndo: true });
            currentTheme.value = theme;

            if (persistTheme) {
                saveTheme(theme);
            }
        } catch (error) {
        } finally {
            isThemeChanging.value = false;
        }
    };

    // 监听外部主题变化
    watch(
        () => externalTheme,
        (newTheme) => {
            if (newTheme && newTheme !== currentTheme.value) {
                applyTheme(newTheme);
            }
        },
        { immediate: true }
    );

    /**
     * 获取当前主题
     * @returns {string} 当前主题
     */
    const getCurrentTheme = () => {
        return currentTheme.value;
    };

    /**
     * 切换主题（内部使用，不暴露给外部）
     * @returns {Promise<string>} 切换后的主题
     */
    const toggleThemeInternal = async () => {
        const newTheme = currentTheme.value === 'light' ? 'dark' : 'light';
        await applyTheme(newTheme);
        return newTheme;
    };

    return {
        currentTheme,
        isThemeChanging,
        applyTheme,
        getCurrentTheme,
        toggleThemeInternal // 仅供内部使用，不建议外部调用
    };
}

/**
 * 便捷方法：创建主题联动
 * @param {Ref} widgetRef - Widget 实例
 * @param {string|Ref<string>} externalTheme - 外部主题
 * @param {Object} options - 选项
 * @returns {Object} 主题管理 API
 */
export function createThemeLinkage(widgetRef, externalTheme, options = {}) {
    return useTheme(widgetRef, externalTheme, options);
}
