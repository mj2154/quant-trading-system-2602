/**
 * Custom Technical Indicators
 * Custom EMA and MACD indicators with configurable parameters
 */

/**
 * Get custom technical indicators
 * @param {Object} PineJS - TradingView PineJS object with standard functions
 * @returns {Promise<Array>} Array of custom indicators
 */
export function getCustomIndicators(PineJS) {
    return Promise.resolve([
        {
            // Internal indicator identifier (not shown in UI)
            name: 'Custom EMA Indicator',

            // Indicator metainfo configuration
            metainfo: {
                _metainfoVersion: 51,
                id: 'custom-ema-indicator@tv-basicstudies-1',
                description: '555 EMA',
                shortDescription: 'Custom EMA',
                is_price_study: true,
                isCustomIndicator: true,

                // Number format
                format: {
                    type: 'price',
                    precision: 4,
                    minTick: 0.0001
                },

                // Define output plots (5 configurable EMA lines)
                plots: [
                    { id: 'ema1', type: 'line', title: 'EMA 1' },
                    { id: 'ema2', type: 'line', title: 'EMA 2' },
                    { id: 'ema3', type: 'line', title: 'EMA 3' },
                    { id: 'ema4', type: 'line', title: 'EMA 4' },
                    { id: 'ema5', type: 'line', title: 'EMA 5' }
                ],

                // User configurable parameters (5 EMA periods)
                inputs: [
                    { id: 'period1', name: 'Period 1', type: 'integer', defval: 5, min: 1, max: 500 },
                    { id: 'period2', name: 'Period 2', type: 'integer', defval: 10, min: 1, max: 500 },
                    { id: 'period3', name: 'Period 3', type: 'integer', defval: 20, min: 1, max: 500 },
                    { id: 'period4', name: 'Period 4', type: 'integer', defval: 60, min: 1, max: 500 },
                    { id: 'period5', name: 'Period 5', type: 'integer', defval: 120, min: 1, max: 500 }
                ],

                // Default styles
                defaults: {
                    styles: {
                        ema1: { color: '#FF0000', linewidth: 1, plottype: 0 },
                        ema2: { color: '#00FF00', linewidth: 1, plottype: 0 },
                        ema3: { color: '#0000FF', linewidth: 1, plottype: 0 },
                        ema4: { color: '#FFFF00', linewidth: 1, plottype: 0 },
                        ema5: { color: '#FF00FF', linewidth: 1, plottype: 0 }
                    },
                    inputs: { period1: 5, period2: 10, period3: 20, period4: 60, period5: 120 }
                },

                styles: {
                    ema1: { title: 'EMA 1' },
                    ema2: { title: 'EMA 2' },
                    ema3: { title: 'EMA 3' },
                    ema4: { title: 'EMA 4' },
                    ema5: { title: 'EMA 5' }
                }
            },

            // Indicator constructor
            constructor: function() {
                this.init = function(context, inputs) {
                    this._context = context;
                    this._input = inputs;
                };

                this.main = function(context, inputs) {
                    this._context = context;
                    this._input = inputs;

                    // Get user input parameters by index
                    var period1 = this._input(0);
                    var period2 = this._input(1);
                    var period3 = this._input(2);
                    var period4 = this._input(3);
                    var period5 = this._input(4);

                    // Use close price
                    var close = PineJS.Std.close(context);
                    var priceVar = context.new_var(close);

                    // Calculate 5 EMA lines with configurable periods
                    var ema1 = PineJS.Std.ema(priceVar, period1, context);
                    var ema2 = PineJS.Std.ema(priceVar, period2, context);
                    var ema3 = PineJS.Std.ema(priceVar, period3, context);
                    var ema4 = PineJS.Std.ema(priceVar, period4, context);
                    var ema5 = PineJS.Std.ema(priceVar, period5, context);

                    return [ema1, ema2, ema3, ema4, ema5];
                };
            }
        },

        // 第二个指标：自定义MACD
        {
            // Internal indicator identifier (not shown in UI)
            name: 'Custom MACD Indicator',

            // Indicator metainfo configuration
            metainfo: {
                _metainfoVersion: 51,
                id: 'custom-macd-indicator@tv-basicstudies-1',
                description: '5555 macd',
                shortDescription: 'Custom MACD',
                is_price_study: false,  // false = 独立副图显示
                isCustomIndicator: true,

                // Number format
                format: {
                    type: 'price',
                    precision: 4,
                    minTick: 0.0001
                },

                // Define output plots (MACD line, Signal line, Histogram with conditional color, Background coloring)
                plots: [
                    {
                        id: 'macd_line',
                        type: 'line',
                        title: 'MACD'
                    },
                    {
                        id: 'macd_colorer',
                        type: 'colorer',
                        target: 'macd_line',
                        palette: 'macdPalette'
                    },
                    {
                        id: 'signal_line',
                        type: 'line',
                        title: 'Signal Line'
                    },
                    {
                        id: 'histogram',
                        type: 'line',
                        title: 'Histogram',
                        histogramBase: 0
                    },
                    {
                        id: 'histogram_colorer',
                        type: 'colorer',
                        target: 'histogram',
                        palette: 'histogramPalette'
                    },
                    {
                        id: 'background_colorer',
                        type: 'bg_colorer',
                        palette: 'backgroundPalette'
                    }
                ],

                // 调色板配置（参考TradingView Pine Script MACD）
                palettes: {
                    macdPalette: {
                        colors: {
                            0: { name: 'MACD < Signal' },
                            1: { name: 'MACD >= Signal' }
                        }
                    },
                    histogramPalette: {
                        colors: {
                            0: { name: 'Above: Growing' },
                            1: { name: 'Above: Falling' },
                            2: { name: 'Below: Growing' },
                            3: { name: 'Below: Falling' }
                        }
                    },
                    backgroundPalette: {
                        colors: {
                            1: { name: 'Golden Cross (Bullish)' },
                            2: { name: 'Death Cross (Bearish)' }
                        },
                        
                    }
                },

                // User configurable parameters
                inputs: [
                    {
                        id: 'fastLength',
                        name: 'Fast Length',
                        type: 'integer',
                        defval: 12,
                        min: 1,
                        max: 100
                    },
                    {
                        id: 'slowLength',
                        name: 'Slow Length',
                        type: 'integer',
                        defval: 26,
                        min: 2,
                        max: 200
                    },
                    {
                        id: 'signalLength',
                        name: 'Signal Length',
                        type: 'integer',
                        defval: 9,
                        min: 1,
                        max: 100
                    }
                ],

                // Default styles and parameters
                defaults: {
                    palettes: {
                        macdPalette: {
                            colors: {
                                0: { color: '#B71D1C', width: 3, style: 0 },  // MACD < Signal (Downtrend) - 深红色
                                1: { color: '#4BAF4F', width: 3, style: 0 }   // MACD >= Signal (Uptrend) - 绿色
                            }
                        },
                        histogramPalette: {
                            colors: {
                                0: { color: '#26A69A', width: 6, style: 0 },  // Above: Growing - 浅绿色
                                1: { color: '#B2DFDB', width: 6, style: 0 },  // Above: Falling - 更浅绿色
                                2: { color: '#FF5252', width: 6, style: 0 },  // Below: Growing - 红色
                                3: { color: '#FFCDD2', width: 6, style: 0 }   // Below: Falling - 浅红色
                            }
                        },
                        backgroundPalette: {
                            colors: {
                                1: { color: 'rgba(0, 255, 0, 0.6)' },          // 金叉 - 半透明绿色
                                2: { color: 'rgba(255, 0, 0, 0.6)' }           // 死叉 - 半透明红色
                            }
                        }
                    },
                    styles: {
                        macd_line: {
                            title: 'MACD',
                            color: '#FF6D00'  // Pine Script MACD线橙色
                        },
                        signal_line: {
                            title: 'Signal',
                            color: '#2962FF'  // Pine Script Signal线蓝色
                        },
                        histogram: {
                            title: 'Histogram',
                            histogramBase: 0,
                            plottype: 5,  // 5 = columns
                        }
                    },
                    inputs: {
                        fastLength: 12,
                        slowLength: 26,
                        signalLength: 9
                    }
                },

                // Plot style settings
                styles: {
                    macd_line: { title: 'MACD' },
                    signal_line: { title: 'Signal' },
                    histogram: { title: 'Histogram', histogramBase: 0 }
                }
            },

            // Indicator constructor
            constructor: function() {
                /**
                 * Initialization function
                 * @param {Object} context - Chart context
                 * @param {Function} inputCallback - Input parameters callback
                 */
                this.init = function(context, inputCallback) {
                    this._context = context;
                    this._input = inputCallback;

                    // No initialization needed
                };

                /**
                 * Main calculation function - called once per bar
                 * @param {Object} context - Chart context
                 * @param {Function} inputCallback - Input parameters callback
                 * @returns {Array} Values for 6 plots (3 lines + 2 colorers + 1 background colorer)
                 */
                this.main = function(context, inputCallback) {
                    this._context = context;
                    this._input = inputCallback;

                    // Get user input parameters
                    const fastLength = inputCallback(0);  // 12
                    const slowLength = inputCallback(1);  // 26
                    const signalLength = inputCallback(2);  // 9

                    // Use close price by default
                    const close = PineJS.Std.close(context);

                    // Create series variable for price
                    const priceVar = context.new_var(close);

                    // Calculate fast EMA (using user-defined period)
                    const fastEMA = PineJS.Std.ema(priceVar, fastLength, context);

                    // Calculate slow EMA (using user-defined period)
                    const slowEMA = PineJS.Std.ema(priceVar, slowLength, context);

                    // Calculate MACD line = fast EMA - slow EMA
                    const macdLine = fastEMA - slowEMA;

                    // Create MACD line series variable
                    const macdSeries = context.new_var(macdLine);

                    // Calculate signal line = EMA of MACD line (using user-defined period)
                    const signalLine = PineJS.Std.ema(macdSeries, signalLength, context);

                    // Calculate histogram = MACD line - signal line
                    const histogram = macdLine - signalLine;

                    // MACD Line color logic (based on comparison with Signal line)
                    const macdColorKey = macdLine >= signalLine ? 1 : 0;  // 1=Uptrend, 0=Downtrend

                    // Histogram color logic (based on position + direction)
                    // Use PineJS built-in functions to determine direction
                    const histogramSeries = context.new_var(histogram);
                    const isHistogramRising = PineJS.Std.rising(histogramSeries, 1, context);  // 1 period
                    const isHistogramFalling = PineJS.Std.falling(histogramSeries, 1, context);

                    let histogramColorKey;
                    if (histogram >= 0) {
                        // Above zero line
                        histogramColorKey = isHistogramRising ? 0 : 1;  // 0=Growing, 1=Falling
                    } else {
                        // Below zero line
                        histogramColorKey = isHistogramFalling ? 2 : 3;  // 2=Growing (more negative), 3=Falling (towards zero)
                    }

                    // Cross detection logic using PineJS.Std.cross()
                    // Check if MACD crosses above Signal (golden cross)
                    const isGoldenCross = PineJS.Std.cross(macdLine, signalLine, context) && macdLine >= signalLine;
                    // Check if MACD crosses below Signal (death cross)
                    const isDeathCross = PineJS.Std.cross(macdLine, signalLine, context) && macdLine <= signalLine;

                    // Return NaN for no signal (no background), only draw on cross events
                    let backgroundColorKey;
                    if (isGoldenCross) {
                        backgroundColorKey = 1;  // Green background
                    } else if (isDeathCross) {
                        backgroundColorKey = 2;  // Red background
                    } else {
                        backgroundColorKey = NaN;  // No background (maintains default grid)
                    }

                    // Return values in same order as plots:
                    // [macd_line, macd_colorer, signal_line, histogram, histogram_colorer, background_colorer]
                    return [
                        macdLine,              // macd_line plot: actual MACD value
                        macdColorKey,          // macd_colorer plot: MACD color key
                        signalLine,            // signal_line plot: actual signal value
                        histogram,             // histogram plot: actual histogram value
                        histogramColorKey,     // histogram_colorer plot: histogram color key
                        backgroundColorKey     // background_colorer plot: cross signal color key
                    ];
                };
            }
        }
    ]);
}
