import { test, expect, type Page } from 'playwright/test'
import { existsSync, readFileSync } from 'fs'
import { resolve } from 'path'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'
function loadEnv() {
  const path = resolve(process.cwd(), '.env.e2e.local')
  if (!existsSync(path)) return
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    const [key, ...rest] = line.trim().split('=')
    if (key && rest.length && !process.env[key]) process.env[key] = rest.join('=')
  }
}
loadEnv()

async function login(page: Page) {
  await page.goto(`${BASE_URL}/admin/login`)
  await page.fill('#admin-email', process.env.E2E_ADMIN_EMAIL || '')
  await page.fill('#admin-password', process.env.E2E_ADMIN_PASSWORD || '')
  await page.getByRole('button', { name: /sign in/i }).click()
  await page.waitForTimeout(1200)
}

async function verifyFinance(page: Page, viewport: { name: string; width: number; height: number }) {
  test.skip(!process.env.E2E_ADMIN_EMAIL || !process.env.E2E_ADMIN_PASSWORD, 'existing operator test credentials unavailable')
  await page.setViewportSize({ width: viewport.width, height: viewport.height })
  await login(page)
  await page.goto(`${BASE_URL}/operator/finance`)
  await expect(page.getByRole('heading', { name: 'Know what Nexus costs.' })).toBeVisible({ timeout: 20000 })
  await expect(page.getByText('Campaign preflight')).toBeVisible()
  await expect(page.getByText('Trading preflight')).toBeVisible()
  await expect(page.getByText('Resource inventory')).toBeVisible()
  const overflow = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth }))
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1)
  await page.screenshot({ path: `reports/rebuild/wp8_14d_finance_${viewport.name}.png`, fullPage: true })
}

test('WP8.14D authenticated Finance desktop evidence', async ({ page }) => {
  await verifyFinance(page, { name: 'desktop', width: 1440, height: 1000 })
})

test('WP8.14D authenticated Finance mobile evidence', async ({ page }) => {
  await verifyFinance(page, { name: 'mobile', width: 390, height: 844 })
})
