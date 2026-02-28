/**
 * TradingView 图表功能测试脚本
 */

const { chromium } = require('playwright');

async function testTradingView() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const results = {
    timestamp: new Date().toISOString(),
    pageLoad: { status: 'pending', error: null, loadTime: null },
    chartVisible: { status: 'pending', details: null },
    klineData: { status: 'pending', details: null },
    watchlist: { status: 'pending', details: null },
    errors: [],
    warnings: []
  };

  page.on('console', (msg) => {
    const text = msg.text();
    if (msg.type() === 'error') {
      results.errors.push(text);
    } else if (msg.type() === 'warning') {
      results.warnings.push(text);
    }
  });

  page.on('pageerror', (error) => {
    results.errors.push(error.message);
  });

  try {
    console.log('正在访问 http://127.0.0.1:5173...');
    const startTime = Date.now();

    await page.goto('http://127.0.0.1:5173', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    const loadTime = Date.now() - startTime;
    results.pageLoad = { status: 'success', loadTime };
    console.log(`页面加载成功，耗时: ${loadTime}ms`);

    // 等待 Vue 应用和 TradingView 加载
    console.log('等待 TradingView 图表加载...');
    await page.waitForTimeout(5000);

    // 检查页面标题
    const title = await page.title();
    console.log(`页面标题: ${title}`);

    // 检查 TradingView widget 容器
    const widgetContainers = await page.locator('.tradingview-widget-container').count();
    console.log(`TradingView widget 容器数量: ${widgetContainers}`);

    if (widgetContainers > 0) {
      results.chartVisible.status = 'success';
      results.chartVisible.details = `找到 ${widgetContainers} 个 widget 容器`;

      // 检查是否有 canvas (图表渲染的标志)
      const canvasCount = await page.locator('canvas').count();
      console.log(`Canvas 元素数量: ${canvasCount}`);

      if (canvasCount > 0) {
        results.klineData.status = 'success';
        results.klineData.details = `检测到 ${canvasCount} 个 canvas 元素`;
      }

      // 检查 widget 内容
      const firstWidget = page.locator('.tradingview-widget-container').first();
      const widgetHTML = await firstWidget.innerHTML();
      console.log(`Widget HTML 长度: ${widgetHTML.length} 字符`);

      // 检查是否有"没有数据"或类似的错误消息
      const noDataMsg = await page.locator('text=这里没有数据').count();
      const noDataText = await page.locator('text=No data').count();
      console.log(`"这里没有数据"消息: ${noDataMsg}`);
      console.log(`"No data"消息: ${noDataText}`);

    } else {
      results.chartVisible.status = 'failed';
      results.chartVisible.details = '未找到 TradingView 容器';
    }

    // 检查 watchlist
    console.log('\n检查 watchlist 功能...');
    const watchlistContainers = await page.locator('.tradingview-widget-container').count();
    if (watchlistContainers > 1) {
      results.watchlist.status = 'success';
      results.watchlist.details = `检测到 ${watchlistContainers - 1} 个 watchlist 相关 widget`;
    }

  } catch (error) {
    console.error('测试过程中出错:', error.message);
    results.pageLoad.status = 'failed';
    results.pageLoad.error = error.message;
    results.errors.push(error.message);
  } finally {
    await browser.close();
  }

  // 输出测试报告
  console.log('\n' + '='.repeat(60));
  console.log('TradingView 图表功能测试报告');
  console.log('='.repeat(60));
  console.log(`测试时间: ${results.timestamp}`);
  console.log(`页面加载: ${results.pageLoad.status} (${results.pageLoad.loadTime || 'N/A'}ms)`);
  console.log(`图表可见: ${results.chartVisible.status} - ${results.chartVisible.details}`);
  console.log(`K线数据: ${results.klineData.status} - ${results.klineData.details}`);
  console.log(`Watchlist: ${results.watchlist.status} - ${results.watchlist.details}`);
  console.log(`错误数: ${results.errors.length}`);
  console.log(`警告数: ${results.warnings.length}`);

  if (results.errors.length > 0) {
    console.log('\n错误详情:');
    results.errors.forEach((err, i) => console.log(`  ${i + 1}. ${err}`));
  }

  return results;
}

testTradingView()
  .then((results) => {
    const hasErrors = results.errors.length > 0;
    console.log(`\n测试完成。总体状态: ${hasErrors ? '存在问题' : '正常'}`);
    process.exit(hasErrors ? 1 : 0);
  })
  .catch((error) => {
    console.error('测试执行失败:', error);
    process.exit(1);
  });
