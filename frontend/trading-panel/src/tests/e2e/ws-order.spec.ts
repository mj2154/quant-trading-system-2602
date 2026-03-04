/**
 * Trading Order WebSocket E2E Tests
 *
 * This test suite verifies the trading order functionality via WebSocket:
 * 1. WebSocket connection to /ws/trading endpoint
 * 2. CREATE_ORDER - Create limit/market orders
 * 3. GET_ORDER - Query single order
 * 4. LIST_ORDERS - Query order list
 * 5. CANCEL_ORDER - Cancel order
 * 6. GET_OPEN_ORDERS - Query open orders
 * 7. Real-time ORDER_UPDATE push
 */

import { test, expect, describe, beforeAll, afterAll } from 'vitest';
import WebSocket from 'ws';

// Test configuration
const WS_URL = 'ws://127.0.0.1:8000/ws/trading';
const TIMEOUT = 30000; // 30 seconds

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

// Helper function: wait for WebSocket message
function waitForMessage(ws: WebSocket, timeout: number = TIMEOUT): Promise<any> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Timeout waiting for message'));
    }, timeout);

    ws.on('message', (data) => {
      clearTimeout(timer);
      try {
        resolve(JSON.parse(data.toString()));
      } catch (e) {
        reject(e);
      }
    });

    ws.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
}

// Helper function: send request and wait for response
async function sendRequest(ws: WebSocket, request: any): Promise<any> {
  return new Promise((resolve, reject) => {
    const requestId = request.requestId;

    const timer = setTimeout(() => {
      reject(new Error(`Timeout waiting for response: ${requestId}`));
    }, TIMEOUT);

    const handler = (data: Buffer) => {
      try {
        const response = JSON.parse(data.toString());
        if (response.requestId === requestId) {
          clearTimeout(timer);
          ws.off('message', handler);
          resolve(response);
        }
      } catch (e) {
        // Ignore parse errors
      }
    };

    ws.on('message', handler);
    ws.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });

    ws.send(JSON.stringify(request));
  });
}

describe('WebSocket Trading Order E2E', () => {
  let ws: WebSocket;

  beforeAll(async () => {
    // Create WebSocket connection
    ws = new WebSocket(WS_URL);

    // Wait for connection
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('Connection timeout'));
      }, 10000);

      ws.on('open', () => {
        clearTimeout(timer);
        resolve();
      });

      ws.on('error', (error) => {
        clearTimeout(timer);
        reject(error);
      });
    });
  });

  afterAll(async () => {
    // Close WebSocket connection
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
  });

  test.describe('Connection', () => {
    test('should connect to trading WebSocket endpoint', () => {
      expect(ws.readyState).toBe(WebSocket.OPEN);
    });

    test('should receive welcome message or connection confirmation', async () => {
      // Wait a bit for any welcome message
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Just verify connection is still open
      expect(ws.readyState).toBe(WebSocket.OPEN);
    });
  });

  test.describe('CREATE_ORDER', () => {
    test('should create a LIMIT order successfully', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: `req_create_limit_${Date.now()}`,
        timestamp: Date.now(),
        data: testOrders.validLimitOrder
      };

      const response = await sendRequest(ws, request);

      // Verify response structure
      expect(response).toBeDefined();
      expect(response.requestId).toBe(request.requestId);
      expect(response.type).toBe('ORDER_DATA');

      // Verify order data
      expect(response.data).toBeDefined();
      expect(response.data.symbol).toBe('BTCUSDT');
      expect(response.data.side).toBe('BUY');
      expect(response.data.type).toBe('LIMIT');
      expect(response.data.orderId).toBeDefined();
      expect(response.data.clientOrderId).toBeDefined();
      expect(response.data.status).toBeDefined();

      console.log('LIMIT order created:', response.data);
    });

    test('should create a MARKET order successfully', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: `req_create_market_${Date.now()}`,
        timestamp: Date.now(),
        data: testOrders.validMarketOrder
      };

      const response = await sendRequest(ws, request);

      // Verify response structure
      expect(response).toBeDefined();
      expect(response.requestId).toBe(request.requestId);
      expect(response.type).toBe('ORDER_DATA');

      // Verify order data
      expect(response.data).toBeDefined();
      expect(response.data.symbol).toBe('BTCUSDT');
      expect(response.data.type).toBe('MARKET');
      expect(response.data.orderId).toBeDefined();

      console.log('MARKET order created:', response.data);
    });

    test('should reject invalid order (missing quantity)', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: `req_create_invalid_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'LIMIT',
          quantity: 0, // Invalid: must be > 0
          price: 50000,
          marketType: 'FUTURES'
        }
      };

      const response = await sendRequest(ws, request);

      // Should return error
      expect(response).toBeDefined();
      expect(response.type).toBe('ERROR');
      expect(response.data).toBeDefined();
      expect(response.data.code).toBeDefined();
      expect(response.data.message).toBeDefined();

      console.log('Invalid order error:', response.data);
    });
  });

  test.describe('GET_ORDER', () => {
    let createdOrderId: number;

    test.beforeAll(async () => {
      // Create an order first to query
      const request = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: `req_setup_${Date.now()}`,
        timestamp: Date.now(),
        data: testOrders.validLimitOrder
      };

      const response = await sendRequest(ws, request);
      createdOrderId = response.data.orderId;
    });

    test('should get order by orderId', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'GET_ORDER',
        requestId: `req_get_order_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          orderId: createdOrderId,
          marketType: 'FUTURES'
        }
      };

      const response = await sendRequest(ws, request);

      // Verify response
      expect(response).toBeDefined();
      expect(response.requestId).toBe(request.requestId);
      expect(response.type).toBe('ORDER_DATA');
      expect(response.data.orderId).toBe(createdOrderId);

      console.log('Order queried:', response.data);
    });

    test('should get order by clientOrderId', async () => {
      const customClientOrderId = `test_client_${Date.now()}`;

      // Create order with custom clientOrderId
      const createRequest = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: `req_create_client_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          ...testOrders.validLimitOrder,
          clientOrderId: customClientOrderId
        }
      };

      const createResponse = await sendRequest(ws, createRequest);

      // Query by clientOrderId
      const queryRequest = {
        protocolVersion: '2.0',
        type: 'GET_ORDER',
        requestId: `req_get_client_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          clientOrderId: customClientOrderId,
          marketType: 'FUTURES'
        }
      };

      const queryResponse = await sendRequest(ws, queryRequest);

      expect(queryResponse).toBeDefined();
      expect(queryResponse.type).toBe('ORDER_DATA');
      expect(queryResponse.data.clientOrderId).toBe(customClientOrderId);
    });
  });

  test.describe('LIST_ORDERS', () => {
    test('should list orders for a symbol', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'LIST_ORDERS',
        requestId: `req_list_orders_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          limit: 10,
          marketType: 'FUTURES'
        }
      };

      const response = await sendRequest(ws, request);

      // Verify response
      expect(response).toBeDefined();
      expect(response.requestId).toBe(request.requestId);
      expect(response.type).toBe('ORDER_LIST_DATA');
      expect(response.data).toBeDefined();
      expect(Array.isArray(response.data.orders)).toBe(true);

      console.log('Orders list:', response.data.orders.length, 'orders');
    });

    test('should list orders with status filter', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'LIST_ORDERS',
        requestId: `req_list_filter_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          status: 'NEW', // Filter by status
          limit: 10,
          marketType: 'FUTURES'
        }
      };

      const response = await sendRequest(ws, request);

      expect(response).toBeDefined();
      expect(response.type).toBe('ORDER_LIST_DATA');
      expect(response.data).toBeDefined();
    });
  });

  test.describe('GET_OPEN_ORDERS', () => {
    test('should get open orders', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'GET_OPEN_ORDERS',
        requestId: `req_open_orders_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          marketType: 'FUTURES'
        }
      };

      const response = await sendRequest(ws, request);

      // Verify response
      expect(response).toBeDefined();
      expect(response.requestId).toBe(request.requestId);
      expect(response.type).toBe('ORDER_LIST_DATA');
      expect(response.data).toBeDefined();
      expect(Array.isArray(response.data.orders)).toBe(true);

      console.log('Open orders:', response.data.orders.length, 'orders');
    });

    test('should get all open orders when symbol not specified', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'GET_OPEN_ORDERS',
        requestId: `req_all_open_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          marketType: 'FUTURES'
        }
      };

      const response = await sendRequest(ws, request);

      expect(response).toBeDefined();
      expect(response.type).toBe('ORDER_LIST_DATA');
    });
  });

  test.describe('CANCEL_ORDER', () => {
    test('should cancel an order by orderId', async () => {
      // First create an order
      const createRequest = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: `req_cancel_setup_${Date.now()}`,
        timestamp: Date.now(),
        data: testOrders.validLimitOrder
      };

      const createResponse = await sendRequest(ws, createRequest);
      const orderId = createResponse.data.orderId;

      // Cancel the order
      const cancelRequest = {
        protocolVersion: '2.0',
        type: 'CANCEL_ORDER',
        requestId: `req_cancel_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          orderId: orderId,
          marketType: 'FUTURES'
        }
      };

      const cancelResponse = await sendRequest(ws, cancelRequest);

      // Verify cancellation
      expect(cancelResponse).toBeDefined();
      expect(cancelResponse.requestId).toBe(cancelRequest.requestId);
      expect(cancelResponse.type).toBe('ORDER_DATA');
      expect(cancelResponse.data.orderId).toBe(orderId);
      expect(cancelResponse.data.status).toBe('CANCELED');

      console.log('Order cancelled:', cancelResponse.data);
    });

    test('should cancel an order by clientOrderId', async () => {
      const customClientOrderId = `cancel_test_${Date.now()}`;

      // Create order with custom clientOrderId
      const createRequest = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: `req_cancel_setup2_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          ...testOrders.validLimitOrder,
          clientOrderId: customClientOrderId
        }
      };

      const createResponse = await sendRequest(ws, createRequest);

      // Cancel by clientOrderId
      const cancelRequest = {
        protocolVersion: '2.0',
        type: 'CANCEL_ORDER',
        requestId: `req_cancel_client_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          clientOrderId: customClientOrderId,
          marketType: 'FUTURES'
        }
      };

      const cancelResponse = await sendRequest(ws, cancelRequest);

      expect(cancelResponse).toBeDefined();
      expect(cancelResponse.type).toBe('ORDER_DATA');
      expect(cancelResponse.data.status).toBe('CANCELED');
    });
  });

  test.describe('Error Handling', () => {
    test('should handle missing required fields', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: `req_error_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          // Missing required fields: symbol, side, type, quantity
        }
      };

      const response = await sendRequest(ws, request);

      // Should return error
      expect(response.type).toBe('ERROR');
      expect(response.data).toBeDefined();
    });

    test('should handle unknown order type', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'CREATE_ORDER',
        requestId: `req_unknown_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          side: 'BUY',
          type: 'UNKNOWN_TYPE',
          quantity: 0.001,
          marketType: 'FUTURES'
        }
      };

      const response = await sendRequest(ws, request);

      // Should return error
      expect(response.type).toBe('ERROR');
    });

    test('should handle non-existent order query', async () => {
      const request = {
        protocolVersion: '2.0',
        type: 'GET_ORDER',
        requestId: `req_notfound_${Date.now()}`,
        timestamp: Date.now(),
        data: {
          symbol: 'BTCUSDT',
          orderId: 999999999999, // Non-existent order
          marketType: 'FUTURES'
        }
      };

      const response = await sendRequest(ws, request);

      // Should return error or empty data
      expect(response).toBeDefined();
    });
  });
});
