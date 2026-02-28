const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const errors = [];
  const logs = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    } else {
      logs.push(`[${msg.type()}] ${msg.text()}`);
    }
  });

  page.on('pageerror', err => {
    errors.push(`Page Error: ${err.message}`);
  });

  try {
    await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle', timeout: 30000 });

    // Wait for the page to fully load
    await page.waitForTimeout(3000);

    console.log('=== Console Logs ===');
    logs.forEach(log => console.log(log));

    console.log('\n=== Console Errors ===');
    errors.forEach(err => console.log('ERROR:', err));

    if (errors.length === 0) {
      console.log('\nNo errors found!');
    }
  } catch (err) {
    console.log('Navigation error:', err.message);
  }

  await browser.close();
})();
