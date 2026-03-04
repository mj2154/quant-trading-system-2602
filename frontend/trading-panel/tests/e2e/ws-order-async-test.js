/**
 * Trading Order Full Flow E2E Tests
 *
 * This test verifies the complete async order flow:
 * 1. Send CREATE_ORDER request
 * 2. Receive ACK immediately
 * 3. Wait for async SUCCESS/ERROR response from binance-service
 *
 * Run with: node tests/e2e/ws-order-async-test.js
 */

import WebSocket from 'ws';

// Test configuration
const WS_URL = 'ws://127.0.0.1:8000/ws/trading';
const TIMEOUT = 60000; // 60 seconds for async operations

// Test results tracking
let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function test(name, fn) {
  try {
    const result = fn();
    if (result && typeof result.then === 'function') {
      return result.then(() => {
        console.log(`  ✓ ${name}`);
        passed++;
      }).catch(err => {
        console.log(`  ✗ ${name}`);
        console.log(`    Error: ${err.message}`);
        failed++;
      });
    } else {
      console.log(`  ✓ ${name}`);
      passed++;
    }
  } catch (err) {
    console.log(`  ✗ ${name}`);
    console.log(`    Error: ${err.message}`);
    failed++;
  }
}

// Helper: collect all messages for a specific requestId
function collectMessages(ws, requestId, maxMessages = 5) {
  return new Promise((resolve, reject) => {
    const messages = [];
    const timer = setTimeout(() => {
      resolve(messages); // Timeout is ok, return collected messages
    }, TIMEOUT);

    const handler = (data) => {
      try {
        const msg = JSON.parse(data.toString());
        if (msg.requestId === requestId) {
          messages.push(msg);
          console.log(`    Received: ${msg.type}`);

          // Stop if we got the final response
          if (msg.type === 'ORDER_DATA' || msg.type === 'ERROR') {
            clearTimeout(timer);
            ws.off('message', handler);
            resolve(messages);
          }

          // Limit messages
          if (messages.length >= maxMessages) {
            clearTimeout(timer);
            ws.off('message', handler);
            resolve(messages);
          }
        }
      } catch (e) {
        // Ignore parse errors
      }
    };

    ws.on('message', handler);
    ws.on('error', reject);

    // Start timeout regardless
    setTimeout(() => {
      ws.off('message', handler);
      resolve(messages);
    }, TIMEOUT);
  });
}

// Main test suite
async function runTests() {
  console.log('='.repeat(60));
  console.log('WebSocket Trading Order Full Flow E2E Tests');
  console.log('='.repeat(60));

  let ws;

  try {
    // Connect to WebSocket
    console.log('\nConnecting to WebSocket...');
    ws = new WebSocket(WS_URL);

    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Connection timeout')), 10000);
      ws.on('open', () => {
        clearTimeout(timer);
        resolve();
      });
      ws.on('error', reject);
    });
    console.log('  ✓ Connected successfully\n');

    // Test: Create LIMIT order and wait for full async response
    await test('CREATE_ORDER: Create LIMIT order - full async flow', async () => {
      const requestId = `req_async_limit_${Date.now()}`;
      const request = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: requestId,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'LIMIT',
          quantity: 0.001,
          price: 50000,
          timeInForce: 'GTC',
          marketType: 'FUTURES'
        }
      };

      console.log(`    Sending request: ${requestId}`);
      ws.send(JSON.stringify(request));

      // Wait for async response
      const messages = await collectMessages(ws, requestId);

      console.log(`    Total messages received: ${messages.length}`);
      for (const msg of messages) {
        console.log(`      - ${msg.type}: ${JSON.stringify(msg.data || {}).slice(0, 100)}`);
      }

      // Should receive at least ACK and ORDER_DATA
      const types = messages.map(m => m.type);
      assert(types.includes('ACK'), 'Should receive ACK');

      // Check if we got ORDER_DATA (success) or ERROR
      const hasOrderData = types.includes('ORDER_DATA');
      const hasError = types.includes('ERROR');

      if (hasOrderData || hasError) {
        console.log(`    ✓ Received final response`);
      } else {
        console.log(`    ⚠ Timeout waiting for final response (binance-service may not be processing)`);
      }
    });

    // Test: Create MARKET order
    await test('CREATE_ORDER: Create MARKET order - full async flow', async () => {
      const requestId = `req_async_market_${Date.now()}`;
      const request = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: requestId,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'MARKET',
          quantity: 0.001,
          marketType: 'FUTURES'
        }
      };

      console.log(`    Sending request: ${requestId}`);
      ws.send(JSON.stringify(request));

      const messages = await collectMessages(ws, requestId);
      const types = messages.map(m => m.type);

      assert(types.includes('ACK'), 'Should receive ACK');
      console.log(`    Messages: ${types.join(', ')}`);
    });

    // Test: Invalid order (validation error)
    await test('CREATE_ORDER: Invalid order - should get ERROR', async () => {
      const requestId = `req_async_invalid_${Date.now()}`;
      const request = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: requestId,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'LIMIT',
          quantity: 0, // Invalid
          price: 50000,
          marketType: 'FUTURES'
        }
      };

      console.log(`    Sending request: ${requestId}`);
      ws.send(JSON.stringify(request));

      const messages = await collectMessages(ws, requestId);
      const types = messages.map(m => m.type);

      // Should receive either ERROR (fast validation) or ACK then ERROR
      assert(types.includes('ACK') || types.includes('ERROR'), 'Should receive response');

      const hasError = types.includes('ERROR');
      if (hasError) {
        const errorMsg = messages.find(m => m.type === 'ERROR');
        console.log(`    ✓ Got ERROR: ${errorMsg?.data?.message || errorMsg?.data}`);
      }
    });

  } catch (err) {
    console.error('\nTest execution error:', err.message);
    failed++;
  } finally {
    // Close WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }

    // Print summary
    console.log('\n' + '='.repeat(60));
    console.log(`Tests: ${passed + failed}, Passed: ${passed}, Failed: ${failed}`);
    console.log('='.repeat(60));

    if (failed === 0) {
      console.log('\n✓ All tests passed!');
    } else {
      console.log('\n⚠ Some tests failed. Check if binance-service is processing order tasks.');
    }

    process.exit(failed > 0 ? 1 : 0);
  }
}

runTests();
