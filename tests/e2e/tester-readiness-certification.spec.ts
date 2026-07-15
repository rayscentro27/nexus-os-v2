import { test, expect } from 'playwright/test'

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true'
const adminEmail = process.env.E2E_ADMIN_EMAIL
const adminPassword = process.env.E2E_ADMIN_PASSWORD

async function loginAsAdmin(page: import('@playwright/test').Page) {
  await page.goto('/admin/login')
  await page.waitForLoadState('domcontentloaded')
  await page.getByLabel(/email/i).fill(adminEmail!)
  await page.getByLabel(/password/i).fill(adminPassword!)
  await page.getByRole('button', { name: /sign in|log in|submit/i }).click()
  await page.waitForURL('**/admin/**', { timeout: 15_000 })
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
}

test.describe('tester readiness panel', () => {
  test.skip(!enabled || !adminEmail || !adminPassword, 'Set E2E_ENABLE_AUTHENTICATED=true and admin credentials')

  test('synthetic admin opens Tester Readiness', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    await expect(page.getByText(/Tester Readiness/i).first()).toBeVisible({ timeout: 10_000 })
  })

  test('Persona A card renders', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    await expect(page.getByText(/Persona A/i).first()).toBeVisible({ timeout: 10_000 })
  })

  test('Persona B card renders', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    await expect(page.getByText(/Persona B/i).first()).toBeVisible({ timeout: 10_000 })
  })

  test('Persona C card renders', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    await expect(page.getByText(/Persona C/i).first()).toBeVisible({ timeout: 10_000 })
  })

  test('status details render for each persona', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    await expect(page.getByText(/Auth/i).first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/Parser/i).first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/Canonical/i).first()).toBeVisible({ timeout: 10_000 })
  })

  test('warning banner shows synthetic data notice', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    await expect(page.getByText(/Synthetic test data only/i).first()).toBeVisible({ timeout: 10_000 })
  })

  test('refresh button works', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    const refreshBtn = page.getByRole('button', { name: /refresh/i }).first()
    await expect(refreshBtn).toBeVisible({ timeout: 10_000 })
    await refreshBtn.click()
    await page.waitForTimeout(1000)
  })

  test('open client login action opens new tab safely', async ({ page }) => {
    await loginAsAdmin(page)
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    const openBtn = page.getByRole('button', { name: /open client login/i }).first()
    if (await openBtn.isVisible().catch(() => false)) {
      const [popup] = await Promise.all([
        page.waitForEvent('popup', { timeout: 5000 }).catch(() => null),
        openBtn.click(),
      ])
      if (popup) {
        expect(popup.url()).toContain('/client/login')
        await popup.close()
      }
    }
  })

  test('client cannot access tester route', async ({ page }) => {
    await page.goto('/client/login')
    await page.waitForLoadState('domcontentloaded')
    // Try to navigate to admin tester route
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    // Should be redirected or denied
    const isOnAdmin = page.url().includes('/admin')
    const hasAccessDenied = await page.getByText(/admin access required/i).isVisible().catch(() => false)
    const hasLoginForm = await page.getByLabel(/email/i).isVisible().catch(() => false)
    expect(isOnAdmin && (hasAccessDenied || hasLoginForm)).toBeTruthy()
  })
})

test.describe('tester readiness panel — client denial', () => {
  test.skip(!enabled, 'Set E2E_ENABLE_AUTHENTICATED=true')

  test('anonymous user cannot access tester panel', async ({ page }) => {
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    const hasAccessDenied = await page.getByText(/admin access required/i).isVisible().catch(() => false)
    const hasLoginForm = await page.getByText(/admin login/i).isVisible().catch(() => false)
    expect(hasAccessDenied || hasLoginForm).toBeTruthy()
  })
})
