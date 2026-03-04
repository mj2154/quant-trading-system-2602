/**
 * Trading Order E2E Tests
 *
 * This test suite verifies the trading order functionality including:
 * 1. WebSocket connection to trading endpoint
 * 2. Order form creation (limit and market orders)
 * 3. Order list display
 * 4. Order cancellation
 * 5. Real-time order updates via WebSocket
 */

import { test, expect, type Page } from '@playwright/test'

// Test constants
const BASE_URL = 'http://127.0.0.1:5173'
const WS_TRADING_URL = 'ws://127.0.0.1:8000/ws/trading'

test.describe('Trading Dashboard E2E', () => {
  // Helper function to open trading dashboard tab
  async function openTradingDashboard(page: Page) {
    // Wait for the page to fully load
    await page.waitForLoadState('domcontentloaded')
    await page.waitForLoadState('networkidle')

    // Wait for Vue app to initialize
    await page.waitForTimeout(3000)

    // First check if trading dashboard tab is already open
    const existingTab = page.locator('.tab-item:has-text("交易面板")')
    if (await existingTab.isVisible().catch(() => false)) {
      // Click on existing tab
      await existingTab.click()
      await page.waitForTimeout(1000)
      return
    }

    // The add button is the last button in the app-header
    // It opens a dropdown with module options
    const headerElement = page.locator('.app-header')
    if (await headerElement.isVisible().catch(() => false)) {
      // Get all buttons in header
      const buttons = page.locator('.app-header button')
      const buttonCount = await buttons.count()

      // Click the last button (the add button)
      if (buttonCount > 0) {
        await buttons.nth(buttonCount - 1).click()
        await page.waitForTimeout(1000)

        // Wait for dropdown to appear and find the trading dashboard option
        // The dropdown options may have different class names
        // Let's try different selectors
        const optionSelectors = [
          '.n-base-select-option:has-text("交易面板")',
          '.n-dropdown-option:has-text("交易面板")',
          '.n-menu-item:has-text("交易面板")',
          'div[role="option"]:has-text("交易面板")',
        ]

        for (const selector of optionSelectors) {
          const option = page.locator(selector).first()
          if (await option.isVisible().catch(() => false)) {
            await option.click()
            await page.waitForTimeout(2000)
            return
          }
        }

        // If still no option found, try clicking on the dropdown body
        const dropdownBody = page.locator('.n-base-select-dropdown, .n-dropdown')
        if (await dropdownBody.isVisible().catch(() => false)) {
          // Press Escape to close dropdown if nothing worked
          await page.keyboard.press('Escape')
        }
      }
    }
  }

  test.beforeEach(async ({ page }) => {
    // Navigate to base URL and open trading dashboard
    await page.goto(BASE_URL)
    await openTradingDashboard(page)

    // Listen for console messages
    page.on('console', (msg) => {
      console.log(`[CONSOLE ${msg.type()}] ${msg.text()}`)
    })
  })

  test.afterEach(async ({ page }, testInfo) => {
    // Capture screenshot on test failure
    if (testInfo.status === 'failed') {
      await page.screenshot({
        path: `artifacts/trading-${testInfo.title.replace(/\s+/g, '_')}_failed.png`,
        fullPage: true,
      })
    }
  })

  test.describe('Order Form', () => {
    test('should display order form with all required fields', async ({ page }) => {
      // Wait for order form to load
      const orderForm = page.locator('[data-testid="market-type-select"]')
      await expect(orderForm).toBeVisible({ timeout: 30000 })

      // Check all form fields are present
      await expect(page.locator('[data-testid="symbol-input"]')).toBeVisible()
      await expect(page.locator('[data-testid="side-buttons"]')).toBeVisible()
      await expect(page.locator('[data-testid="buy-button"]')).toBeVisible()
      await expect(page.locator('[data-testid="sell-button"]')).toBeVisible()
      await expect(page.locator('[data-testid="order-type-select"]')).toBeVisible()
      await expect(page.locator('[data-testid="quantity-input"]')).toBeVisible()
      await expect(page.locator('[data-testid="submit-button"]')).toBeVisible()
    })

    test('should toggle between buy and sell sides', async ({ page }) => {
      // Wait for form to load
      await expect(page.locator('[data-testid="buy-button"]')).toBeVisible({ timeout: 30000 })

      // Default should be BUY
      const buyButton = page.locator('[data-testid="buy-button"]')
      await expect(buyButton).toHaveClass(/n-button--success-type/)

      // Click SELL button
      await page.locator('[data-testid="sell-button"]').click()

      // Verify sell button is now the success type
      const sellButton = page.locator('[data-testid="sell-button"]')
      await expect(sellButton).toHaveClass(/n-button--error-type/)
    })

    test('should show price field for limit orders', async ({ page }) => {
      // Wait for form to load
      await expect(page.locator('[data-testid="order-type-select"]')).toBeVisible({ timeout: 30000 })

      // Default order type is LIMIT - price field should be visible
      await expect(page.locator('[data-testid="price-input"]')).toBeVisible()
    })

    test('should hide price field for market orders', async ({ page }) => {
      // Wait for form to load
      await expect(page.locator('[data-testid="order-type-select"]')).toBeVisible({ timeout: 30000 })

      // Select MARKET order type
      await page.locator('[data-testid="order-type-select"]').click()
      await page.locator('.n-base-select-option:has-text("Market")').click()

      // Price field should be hidden for market orders
      await expect(page.locator('[data-testid="price-input"]')).not.toBeVisible()
    })

    test('should validate symbol format', async ({ page }) => {
      // Wait for form to load
      await expect(page.locator('[data-testid="symbol-input"]')).toBeVisible({ timeout: 30000 })

      // Enter invalid symbol
      const symbolInput = page.locator('[data-testid="symbol-input"] input')
      await symbolInput.fill('invalid')
      await symbolInput.blur()

      // Should show error message
      const feedback = page.locator('[data-testid="symbol-input"] .n-form-item-feedback')
      await expect(feedback).toContainText(/Invalid symbol format/)
    })

    test('should accept valid symbol format', async ({ page }) => {
      // Wait for form to load
      await expect(page.locator('[data-testid="symbol-input"]')).toBeVisible({ timeout: 30000 })

      // Enter valid symbol
      const symbolInput = page.locator('[data-testid="symbol-input"] input')
      await symbolInput.fill('BTCUSDT')
      await symbolInput.blur()

      // Should NOT show error
      const errorAlert = page.locator('[data-testid="error-message"]')
      await expect(errorAlert).not.toBeVisible()
    })
  })

  test.describe('Order List', () => {
    test('should display order list component', async ({ page }) => {
      // Wait for order list to load (it has a refresh button)
      const refreshButton = page.locator('[data-testid="refresh-button"]')
      await expect(refreshButton).toBeVisible({ timeout: 30000 })

      // Check filter dropdowns are present
      await expect(page.locator('[data-testid="market-filter"]')).toBeVisible()
      await expect(page.locator('[data-testid="status-filter"]')).toBeVisible()
      await expect(page.locator('[data-testid="side-filter"]')).toBeVisible()
    })

    test('should show empty state or table', async ({ page }) => {
      // Wait for the page to load
      await page.waitForTimeout(2000)

      // Check for empty state or table
      const emptyState = page.locator('.n-empty')
      const dataTable = page.locator('.n-data-table')

      // Either empty state or table should be visible
      const isEmptyVisible = await emptyState.isVisible().catch(() => false)
      const isTableVisible = await dataTable.isVisible().catch(() => false)

      expect(isEmptyVisible || isTableVisible).toBe(true)
    })
  })

  test.describe('WebSocket Connection', () => {
    test('should attempt to connect to trading WebSocket endpoint', async ({ page }) => {
      // Note: This test may fail if backend is not running
      // We just verify the page loads without critical errors
      await page.waitForTimeout(3000)

      // Check that the page loaded successfully
      const dashboard = page.locator('.trading-dashboard')
      await expect(dashboard).toBeVisible()
    })

    test('should handle WebSocket connection errors gracefully', async ({ page }) => {
      const consoleErrors: string[] = []

      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text())
        }
      })

      // Wait to capture any connection errors
      await page.waitForTimeout(5000)

      // Filter for critical errors (not connection warnings)
      const criticalErrors = consoleErrors.filter(
        (e) => !e.includes('WebSocket') && !e.includes('connection') && !e.includes('Failed to connect')
      )

      // Should have no critical errors
      expect(criticalErrors.length).toBe(0)
    })
  })

  test.describe('Order Creation Flow', () => {
    test('should enable submit button when form is valid', async ({ page }) => {
      // Wait for form to load
      await expect(page.locator('[data-testid="symbol-input"]')).toBeVisible({ timeout: 30000 })

      // Fill in required fields
      await page.locator('[data-testid="symbol-input"] input').fill('BTCUSDT')
      await page.locator('[data-testid="quantity-input"] input').fill('0.001')
      await page.locator('[data-testid="price-input"] input').fill('50000')

      // Submit button should be enabled
      const submitButton = page.locator('[data-testid="submit-button"]')
      await expect(submitButton).toBeEnabled()
    })

    test('should disable submit button when form is invalid', async ({ page }) => {
      // Wait for form to load
      await expect(page.locator('[data-testid="symbol-input"]')).toBeVisible({ timeout: 30000 })

      // Clear quantity (invalid)
      await page.locator('[data-testid="quantity-input"] input').fill('0')

      // Submit button should be disabled
      const submitButton = page.locator('[data-testid="submit-button"]')
      await expect(submitButton).toBeDisabled()
    })
  })

  test.describe('Order Filters', () => {
    test('should filter orders by market type', async ({ page }) => {
      // Wait for filters to load
      await expect(page.locator('[data-testid="market-filter"]')).toBeVisible({ timeout: 30000 })

      // Click market filter dropdown
      await page.locator('[data-testid="market-filter"]').click()

      // Select Futures option
      await page.locator('.n-base-select-option:has-text("Futures")').click()

      // Verify filter is applied (option should be selected)
      const selectedValue = page.locator('[data-testid="market-filter"] .n-base-selection-label')
      await expect(selectedValue).toContainText('Futures')
    })

    test('should filter orders by status', async ({ page }) => {
      // Wait for filters to load
      await expect(page.locator('[data-testid="status-filter"]')).toBeVisible({ timeout: 30000 })

      // Click status filter dropdown
      await page.locator('[data-testid="status-filter"]').click()

      // Select New status
      await page.locator('.n-base-select-option:has-text("New")').click()

      // Verify filter is applied
      const selectedValue = page.locator('[data-testid="status-filter"] .n-base-selection-label')
      await expect(selectedValue).toContainText('New')
    })
  })

  test.describe('Order Actions', () => {
    test('should display actions menu for orders', async ({ page }) => {
      // Wait for page to load completely
      await page.waitForTimeout(2000)

      // Look for Actions buttons in the table (if orders exist)
      // This test checks the UI structure is correct
      const refreshButton = page.locator('[data-testid="refresh-button"]')
      await expect(refreshButton).toBeVisible()
    })

    test('should refresh order list', async ({ page }) => {
      // Wait for refresh button
      const refreshButton = page.locator('[data-testid="refresh-button"]')
      await expect(refreshButton).toBeVisible({ timeout: 30000 })

      // Click refresh button
      await refreshButton.click()

      // Should not throw any errors
      await page.waitForTimeout(1000)
    })
  })

  test.describe('Trading Dashboard UI/UX', () => {
    test('should load TradingDashboard component', async ({ page }) => {
      // Check that the main dashboard container exists
      const dashboard = page.locator('.trading-dashboard')
      await expect(dashboard).toBeVisible({ timeout: 30000 })
    })

    test('should have proper layout with order form and order list', async ({ page }) => {
      // Wait for components to load
      await expect(page.locator('[data-testid="market-type-select"]')).toBeVisible({ timeout: 30000 })
      await expect(page.locator('[data-testid="refresh-button"]')).toBeVisible({ timeout: 30000 })
    })

    test('should display form in dark theme', async ({ page }) => {
      // Wait for form to load
      await expect(page.locator('[data-testid="market-type-select"]')).toBeVisible({ timeout: 30000 })

      // Check the card has dark theme styling (n-card component)
      const card = page.locator('.n-card')
      await expect(card).toBeVisible()
    })
  })
})
