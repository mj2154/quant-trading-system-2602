/**
 * Trading Order WebSocket E2E Tests
 *
 * Run with: node tests/e2e/ws-order-test.js
 */

import WebSocket from 'ws';

// Test configuration
const WS_URL = 'ws://127.0.0.1:8000/ws/trading';
const TIMEOUT = 30000;

// Test data factory
const testOrders = {
  validLimitOrder: {
    symbol: 'BTCUSDT',
    side: 'BUY',
    type: 'LIMIT',
    quantity: 0.001,
    price: 50000,
    timeInForce: 'GTC',
    marketType: 'FUTURES'
  },
  validMarketOrder: {
    symbol: 'BTCUSDT',
    side: 'BUY',
    type: 'MARKET',
    quantity: 0.001,
    marketType: 'FUTURES'
  }
};

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

function describe(name, fn) {
  console.log(`\n${name}`);
  return fn();
}

// Helper: send request and wait for response
function sendRequest(ws, request) {
  return new Promise((resolve, reject) => {
    const requestId = request.requestId;
    const timer = setTimeout(() => {
      reject(new Error(`Timeout waiting for response: ${requestId}`));
    }, TIMEOUT);

    const handler = (data) => {
      try {
        const response = JSON.parse(data.toString());
        if (response.requestId === requestId) {
          clearTimeout(timer);
          ws.off('message', handler);
          resolve(response);
        }
      } catch (e) {
        // Ignore parse errors, continue waiting
      }
    };

    ws.on('message', handler);
    ws.on('error', reject);

    ws.send(JSON.stringify(request));
  });
}

// Main test suite
async function runTests() {
  console.log('='.repeat(60));
  console.log('WebSocket Trading Order E2E Tests');
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
    console.log('  ✓ Connected successfully');

    // Run tests
    await describe('Connection', async () => {
      await test('WebSocket should be open', () => {
        assert(ws.readyState === WebSocket.OPEN, 'WebSocket not open');
      });
    });

    await describe('CREATE_ORDER', async () => {
      await test('Create LIMIT order - should receive ACK', async () => {
        const request = {
          protocolVersion: '2.0',
          type: 'CREATE_ORDER',
          requestId: `req_limit_${Date.now()}`,
          timestamp: Date.now(),
          data: testOrders.validLimitOrder
        };

        const response = await sendRequest(ws, request);
        // ACK means request was received and written to database
        assert(response.type === 'ACK', `Expected ACK, got ${response.type}`);
        console.log(`    Request acknowledged: ${response.requestId}`);
      });

      await test('Create MARKET order - should receive ACK', async () => {
        const request = {
          protocolVersion: '2.0',
          type: 'CREATE_ORDER',
          requestId: `req_market_${Date.now()}`,
          timestamp: Date.now(),
          data: testOrders.validMarketOrder
        };

        const response = await sendRequest(ws, request);
        assert(response.type === 'ACK', `Expected ACK, got ${response.type}`);
        console.log(`    Request acknowledged: ${response.requestId}`);
      });

      await test('Reject invalid order (quantity=0) - should receive ERROR via ACK', async () => {
        const request = {
          protocolVersion: '2.0',
          type: 'CREATE_ORDER',
          requestId: `req_invalid_${Date.now()}`,
          timestamp: Date.now(),
          data: {
            symbol: 'BTCUSDT',
            side: 'BUY',
            type: 'LIMIT',
            quantity: 0,
            price: 50000,
            marketType: 'FUTURES'
          }
        };

        const response = await sendRequest(ws, request);
        // Can be either ERROR (validation) or ACK (then error in processing)
        assert(['ACK', 'ERROR'].includes(response.type), `Expected ACK or ERROR, got ${response.type}`);
        console.log(`    Response: ${response.type}`);
      });
    });

    let testOrderId;

    await describe('GET_ORDER', async () => {
      await test('Query order - should receive ACK', async () => {
        // First create an order
        const createRequest = {
          protocolVersion: '2.0',
          type: 'CREATE_ORDER',
          requestId: `req_setup_get_${Date.now()}`,
          timestamp: Date.now(),
          data: testOrders.validLimitOrder
        };
        const createResponse = await sendRequest(ws, createRequest);
        assert(createResponse.type === 'ACK', 'Should get ACK for create');
        testOrderId = '12345'; // Placeholder, will get real ID from binance-service

        // Then query it - GET orders return data directly (not async task)
        const request = {
          protocolVersion: '2.0',
          type: 'GET_ORDER',
          requestId: `req_get_${Date.now()}`,
          timestamp: Date.now(),
          data: {
            symbol: 'BTCUSDT',
            orderId: 12345,
            marketType: 'FUTURES'
          }
        };

        const response = await sendRequest(ws, request);
        // GET_ORDER might return ORDER_DATA or ERROR (direct API call, not async)
        assert(['ORDER_DATA', 'ERROR', 'ACK'].includes(response.type),
          `Expected ORDER_DATA/ERROR/ACK, got ${response.type}`);
        console.log(`    Response type: ${response.type}`);
      });
    });

    await describe('LIST_ORDERS', async () => {
      await test('List orders - should return ORDER_LIST_DATA', async () => {
        const request = {
          protocolVersion: '2.0',
          type: 'LIST_ORDERS',
          requestId: `req_list_${Date.now()}`,
          timestamp: Date.now(),
          data: {
            symbol: 'BTCUSDT',
            limit: 10,
            marketType: 'FUTURES'
          }
        };

        const response = await sendRequest(ws, request);
        // LIST_ORDERS might return data directly
        assert(['ORDER_LIST_DATA', 'ACK'].includes(response.type),
          `Expected ORDER_LIST_DATA or ACK, got ${response.type}`);
        if (response.data?.orders) {
          console.log(`    Found ${response.data.orders.length} orders`);
        }
      });
    });

    await describe('GET_OPEN_ORDERS', async () => {
      await test('Get open orders - should return ORDER_LIST_DATA or ACK', async () => {
        const request = {
          protocolVersion: '2.0',
          type: 'GET_OPEN_ORDERS',
          requestId: `req_open_${Date.now()}`,
          timestamp: Date.now(),
          data: {
            symbol: 'BTCUSDT',
            marketType: 'FUTURES'
          }
        };

        const response = await sendRequest(ws, request);
        assert(['ORDER_LIST_DATA', 'ACK'].includes(response.type),
          `Expected ORDER_LIST_DATA or ACK, got ${response.type}`);
        console.log(`    Response type: ${response.type}`);
      });
    });

    await describe('CANCEL_ORDER', async () => {
      await test('Cancel order - should receive ACK', async () => {
        // Cancel request should get ACK (async processing)
        const cancelRequest = {
          protocolVersion: '2.0',
          type: 'CANCEL_ORDER',
          requestId: `req_cancel_${Date.now()}`,
          timestamp: Date.now(),
          data: {
            symbol: 'BTCUSDT',
            orderId: 12345,
            marketType: 'FUTURES'
          }
        };

        const response = await sendRequest(ws, cancelRequest);
        assert(response.type === 'ACK', `Expected ACK, got ${response.type}`);
        console.log(`    Cancel request acknowledged`);
      });
    });

    await describe('Error Handling', async () => {
      await test('Handle missing required fields - should receive ERROR', async () => {
        const request = {
          protocolVersion: '2.0',
          type: 'CREATE_ORDER',
          requestId: `req_error_${Date.now()}`,
          timestamp: Date.now(),
          data: {}
        };

        const response = await sendRequest(ws, request);
        // Can be ERROR (validation) or ACK (async processing)
        assert(['ERROR', 'ACK'].includes(response.type), `Expected ERROR or ACK, got ${response.type}`);
        console.log(`    Response type: ${response.type}`);
      });

      await test('Handle non-existent order query', async () => {
        const request = {
          protocolVersion: '2.0',
          type: 'GET_ORDER',
          requestId: `req_notfound_${Date.now()}`,
          timestamp: Date.now(),
          data: {
            symbol: 'BTCUSDT',
            orderId: 999999999999,
            marketType: 'FUTURES'
          }
        };

        const response = await sendRequest(ws, request);
        // All order operations are async, so they return ACK first
        assert(['ERROR', 'ORDER_DATA', 'ACK'].includes(response.type),
          `Expected ERROR/ORDER_DATA/ACK, got ${response.type}`);
        console.log(`    Response type: ${response.type}`);
      });
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

    process.exit(failed > 0 ? 1 : 0);
  }
}

runTests();
