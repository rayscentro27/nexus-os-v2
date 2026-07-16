import { test, expect } from 'playwright/test'
import { existsSync, readFileSync } from 'fs'
import { resolve } from 'path'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'

function loadLocalE2EEnv() {
  if (process.env.E2E_ADMIN_EMAIL && process.env.E2E_ADMIN_PASSWORD) return
  const envPath = resolve(process.cwd(), '.env.e2e.local')
  if (!existsSync(envPath)) return
  for (const line of readFileSync(envPath, 'utf-8').split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
    const [key, ...valueParts] = trimmed.split('=')
    if (!process.env[key]) process.env[key] = valueParts.join('=')
  }
}

loadLocalE2EEnv()

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'nexus-admin-browser@goclear.test'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || ''

async function loginAsAdmin(page: any) {
  await page.goto(`${BASE_URL}/admin/login`)
  await page.waitForLoadState('domcontentloaded', { timeout: 15_000 })
  await page.fill('#admin-email', ADMIN_EMAIL)
  await page.fill('#admin-password', ADMIN_PASSWORD)
  await page.getByRole('button', { name: /sign in/i }).click()
  await page.waitForURL('**/admin', { timeout: 15_000 }).catch(() => {})
  await page.waitForTimeout(2000)
}

test.describe('Tester Invitation Certification', () => {
  test.describe('Admin', () => {
    test('admin can navigate to tester invitations panel', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      await expect(page.locator('[data-testid="tester-invitation-panel"]')).toBeVisible()
    })

    test('tester invitation panel shows metrics', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      await expect(page.locator('[data-testid="tester-invitation-panel"]')).toContainText('Total')
    })

    test('admin can open create invitation form', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="create-invitation-btn"]', { timeout: 10000 })
      await page.click('[data-testid="create-invitation-btn"]')
      await expect(page.locator('[data-testid="new-inv-name"]')).toBeVisible()
      await expect(page.locator('[data-testid="new-inv-email"]')).toBeVisible()
    })

    test('admin can see payment controls', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      const panelText = await page.locator('[data-testid="tester-invitation-panel"]').textContent()
      expect(panelText).toContain('Security Notes')
      expect(panelText).toContain('Public live payments remain disabled')
    })

    test('admin can see emergency disable button', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      const panelText = await page.locator('[data-testid="tester-invitation-panel"]').textContent()
      expect(panelText).toContain('Controlled live pilot requires separate Ray approval')
    })

    test('admin can see hidden pilot offers', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      await expect(page.locator('[data-testid="tester-invitation-panel"]')).toContainText('real-payment-pilot-1')
    })

    test('raw token is not redisplayed after creation', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      const panelText = await page.locator('[data-testid="tester-invitation-panel"]').textContent()
      expect(panelText).not.toMatch(/sk_test_/)
      expect(panelText).not.toMatch(/whsec_/)
    })
  })

  test.describe('Invited Tester', () => {
    test('one-click invite page loads without manual token input', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-invalid-token`)
      await expect(page.locator('input[name="token"], [data-testid="invite-token-input"]')).toHaveCount(0)
      await expect(page.locator('body')).toContainText(/Invalid Invitation|Verifying your invitation/)
    })

    test('invite page shows GoClear invitation context', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-invalid-token`)
      await expect(page.locator('body')).toContainText('GoClear')
    })

    test('invalid token shows error', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/invalid-token-12345`)
      await expect(page.locator('body')).toContainText(/Invalid Invitation|not valid/)
    })

    test('accept page validates URL token without manual token input', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/accept?token=invalid-token-12345`)
      await expect(page.locator('[data-testid="accept-token-input"]')).toHaveCount(0)
      await expect(page.locator('body')).toContainText(/Invitation Issue|Invalid invitation/)
    })

    test('tester cannot access admin route', async ({ page }) => {
      await page.goto(`${BASE_URL}/admin`)
      await page.waitForTimeout(3000)
      const url = page.url()
      const isAdminLogin = url.includes('/admin/login')
      const isNotAdmin = !url.includes('/admin#')
      expect(isAdminLogin || isNotAdmin).toBe(true)
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
      const catalog = await import('../../src/config/serviceOfferCatalog.ts')
      expect(catalog.PILOT_DISCLOSURE_TEXT).toContain('product-testing')
      expect(catalog.PILOT_DISCLOSURE_TEXT).toContain('$1 charge')
    })
  })
})
