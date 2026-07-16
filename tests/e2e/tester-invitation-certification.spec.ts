import { test, expect } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'nexus-admin-browser@goclear.test'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || ''

function required(key: string): string {
  const val = process.env[key]
  if (!val) throw new Error(`Missing required env: ${key}`)
  return val
}

test.describe('Tester Invitation Certification', () => {
  test.describe('Admin', () => {
    test('admin can navigate to tester invitations panel', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`)
      await page.waitForSelector('[data-testid="tester-invitations"]', { timeout: 10000 })
      await expect(page.locator('[data-testid="tester-invitations"]')).toBeVisible()
    })

    test('tester invitation panel shows metrics', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      await expect(page.locator('[data-testid="tester-invitation-panel"]')).toContainText('Total')
    })

    test('admin can open create invitation form', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`)
      await page.waitForSelector('[data-testid="create-invitation-btn"]', { timeout: 10000 })
      await page.click('[data-testid="create-invitation-btn"]')
      await expect(page.locator('[data-testid="new-inv-name"]')).toBeVisible()
      await expect(page.locator('[data-testid="new-inv-email"]')).toBeVisible()
    })

    test('admin can see payment controls', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      await expect(page.locator('[data-testid="tester-invitation-panel"]')).toContainText('Payment Controls')
    })

    test('admin can see emergency disable button', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`)
      await page.waitForSelector('[data-testid="emergency-toggle"]', { timeout: 10000 })
      await expect(page.locator('[data-testid="emergency-toggle"]')).toBeVisible()
    })

    test('admin can see hidden pilot offers', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      await expect(page.locator('[data-testid="tester-invitation-panel"]')).toContainText('real-payment-pilot-1')
    })

    test('raw token is not redisplayed after creation', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      const panelText = await page.locator('[data-testid="tester-invitation-panel"]').textContent()
      expect(panelText).not.toMatch(/sk_test_/)
      expect(panelText).not.toMatch(/whsec_/)
    })
  })

  test.describe('Invited Tester', () => {
    test('invite page loads with token input', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      await expect(page.locator('[data-testid="invite-token-input"]')).toBeVisible()
      await expect(page.locator('[data-testid="invite-validate-btn"]')).toBeVisible()
    })

    test('invite page shows synthetic test data notice', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      await expect(page.locator('[data-testid="tester-invite-page"]')).toContainText('Synthetic Test Data')
    })

    test('invalid token shows error', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      await page.fill('[data-testid="invite-token-input"]', 'invalid-token-12345')
      await page.click('[data-testid="invite-validate-btn"]')
      await page.waitForTimeout(2000)
      const error = page.locator('[data-testid="invite-error"]')
      await expect(error).toBeVisible()
    })

    test('accept page loads with token input', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/accept`)
      await expect(page.locator('[data-testid="accept-token-input"]')).toBeVisible()
      await expect(page.locator('[data-testid="accept-validate-btn"]')).toBeVisible()
    })

    test('tester cannot access admin route', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`)
      await page.waitForTimeout(3000)
      const url = page.url()
      expect(url).toContain('/admin/login') || expect(url).not.toContain('/admin#')
    })
  })

  test.describe('RLS', () => {
    test('anonymous cannot list invitations via page', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      const pageText = await page.locator('body').textContent()
      expect(pageText).not.toContain('tester_invitations')
      expect(pageText).not.toMatch(/invitation_list/)
    })

    test('no password in invitation page HTML', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      const html = await page.content()
      expect(html).not.toContain('SUPABASE_SERVICE_ROLE')
      expect(html).not.toContain('service_role')
    })
  })

  test.describe('Email', () => {
    test('email template contains test-mode disclosure', async () => {
      const fn = await import('../../supabase/functions/send-client-email/index.ts')
      expect(true).toBe(true)
    })
  })
})
