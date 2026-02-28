/**
 * TradingView 指标配置
 * 将硬编码指标外部化，支持动态配置
 */

export const DEFAULT_INDICATORS = [
    {
        id: 'custom-5ema-indicator@tv-basicstudies-1',  // 保持与 custom-indicators.js 一致
        name: '5EMA',
        description: '5555 5EMA',  // TradingView createStudy 使用的描述符
        enabled: true,
        params: {
            "showLabelsOnPriceScale": false
        }
    },
    {
        id: 'custom-macd-indicator@tv-basicstudies-1',  // 保持与 custom-indicators.js 一致
        name: 'MACD',
        description: '5555 macd',  // TradingView createStudy 使用的描述符
        enabled: true,
        params: {
            "showLabelsOnPriceScale": false
        }
    }
];

/*
说明：
- description 字段应与 custom-indicators.js 中的 description 一致
- 这是 TradingView createStudy() 方法实际使用的标识符
- 参数格式应与 TradingView 指标参数要求匹配
*/
