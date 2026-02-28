/**
 * TradingView 图表功能测试脚本
 * 测试内容：
 * 1. 页面加载和基本元素
 * 2. TradingView 图表是否正常显示
 * 3. K 线数据是否加载
 * 4. watchlist 功能测试
 */

import { chromium } from '@playwright/test';

async function testTradingView() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const results = {
    timestamp: new Date().toISOString(),
    pageLoad: { status: 'pending', error: null },
    consoleMessages: [],
    chartVisible: { status: 'pending', details: null },
    klineData: { status: 'pending', details: null },
    watchlist: { status: 'pending', details: null },
    errors: [],
    warnings: []
  };

  // 监听控制台消息
  page.on('console', (msg) => {
    const type = msg.type();
    const text = msg.text();
    results.consoleMessages.push({ type, text, timestamp: Date.now() });

    if (type === 'error') {
      results.errors.push(text);
    } else if (type === 'warning') {
      results.warnings.push(text);
    }
  });

  // 监听页面错误
  page.on('pageerror', (error) => {
    results.errors.push(error.message);
  });

  try {
    console.log('正在访问 http://127.0.0.1:5173...');
    const startTime = Date.now();

    // 访问页面
    await page.goto('http://127.0.0.1:5173', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    const loadTime = Date.now() - startTime;
    results.pageLoad = { status: 'success', loadTime };

    console.log(`页面加载成功，耗时: ${loadTime}ms`);

    // 等待 Vue 应用挂载
    await page.waitForTimeout(2000);

    // 检查页面标题
    const title = await page.title();
    console.log(`页面标题: ${title}`);

    // 检查是否存在标签页
    const tabExists = await page.locator('.n-tabs').count() > 0 ||
                      await page.locator('[class*="tabs"]').count() > 0;
    console.log(`标签页存在: ${tabExists}`);

    // 等待 TradingView 图表加载
    console.log('等待 TradingView 图表加载...');
    await page.waitForTimeout(3000);

    // 检查 TradingView 相关元素
    const tvContainer = await page.locator('.tradingview-widget-container').count() > 0 ||
                        await page.locator('[class*="tradingview"]').count() > 0;
    const tvWidget = await page.locator('.tradingview-widget-container').first();

    if (tvContainer) {
      results.chartVisible.status = 'success';
      results.chartVisible.details = 'TradingView 容器存在';

      // 检查容器是否有内容
      const containerHTML = await tvWidget.innerHTML();
      const hasContent = containerHTML.length > 100;
      const hasCanvas = await page.locator('canvas').count() > 0;

      console.log(`TradingView 容器有内容: ${hasContent} (${containerHTML.length} chars)`);
      console.log(`页面 Canvas 数量: ${await page.locator('canvas').count()}`);

      if (hasCanvas) {
        results.klineData.status = 'success';
        results.klineData.details = '检测到 canvas 元素，图表可能已渲染';
      }
    } else {
      results.chartVisible.status = 'failed';
      results.chartVisible.details = '未找到 TradingView 容器';
    }

    // 检查 watchlist
    console.log('\n检查 watchlist...');
    const watchlistContainer = await page.locator('[class*="watchlist"]').count() > 0 ||
                                await page.locator('.tradingview-widget-container').count() > 1;

    if (watchlistContainer) {
      results.watchlist.status = 'success';
      results.watchlist.details = 'Watchlist 容器存在';

      // 获取所有 widget 容器数量
      const widgetCount = await page.locator('.tradingview-widget-container').count();
      console.log(`TradingView widget 容器数量: ${widgetCount}`);

      // 查找可能包含交易对的元素
      const watchlistItems = await page.locator('[class*="item"]').count();
      console.log(`可能的 watchlist 项目数: ${watchlistItems}`);
    } else {
      results.watchlist.status = 'pending';
      results.watchlist.details = '未检测到 watchlist';
    }

    // 等待更多数据加载
    await page.waitForTimeout(2000);

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
  if (results.pageLoad.error) {
    console.log(`  错误: ${results.pageLoad.error}`);
  }
  console.log(`图表可见: ${results.chartVisible.status} - ${results.chartVisible.details}`);
  console.log(`K线数据: ${results.klineData.status} - ${results.klineData.details}`);
  console.log(`Watchlist: ${results.watchlist.status} - ${results.watchlist.details}`);
  console.log(`错误数: ${results.errors.length}`);
  console.log(`警告数: ${results.warnings.length}`);

  if (results.errors.length > 0) {
    console.log('\n错误详情:');
    results.errors.forEach((err, i) => console.log(`  ${i + 1}. ${err}`));
  }

  if (results.warnings.length > 0) {
    console.log('\n警告详情:');
    results.warnings.forEach((warn, i) => console.log(`  ${i + 1}. ${warn}`));
  }

  console.log('\n控制台消息统计:');
  const msgByType = results.consoleMessages.reduce((acc, msg) => {
    acc[msg.type] = (acc[msg.type] || 0) + 1;
    return acc;
  }, {});
  console.log(msgByType);

  return results;
}

// 运行测试
testTradingView()
  .then((results) => {
    const hasErrors = results.errors.length > 0 &&
                      !results.errors.every(e => e.includes('WebSocket') || e.includes('favicon'));
    console.log(`\n测试完成。总体状态: ${hasErrors ? '存在问题' : '正常'}`);
    process.exit(hasErrors ? 1 : 0);
  })
  .catch((error) => {
    console.error('测试执行失败:', error);
    process.exit(1);
  });
