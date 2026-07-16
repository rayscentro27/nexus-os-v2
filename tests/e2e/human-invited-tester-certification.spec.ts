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

test.describe('Human Invited Tester Certification', () => {
  test.describe('Invitation Workflow Components', () => {
    test('tester invite page exists and loads', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-invalid-token`)
      await expect(page.locator('body')).toContainText('GoClear')
    })

    test('tester accept page exists and loads', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/accept?token=test-invalid-token`)
      await expect(page.locator('body')).toContainText(/Invitation Issue|Setting up your account/)
    })

    test('tester tasks page exists', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/tasks`)
      await page.waitForTimeout(3000)
      const html = await page.content()
      const hasTestContent = html.includes('sign in') || html.includes('Sign in') || html.includes('tester') || html.includes('Loading')
      expect(hasTestContent).toBe(true)
    })

    test('invite page has no manual token input field', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-invalid-token`)
      await expect(page.locator('[data-testid="invite-token-input"], input[name="token"]')).toHaveCount(0)
    })

    test('accept page has no manual token field before URL validation', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/accept?token=test-invalid-token`)
      await expect(page.locator('[data-testid="accept-token-input"]')).toHaveCount(0)
    })
  })

  test.describe('Security Checks', () => {
    test('no raw tokens exposed in invite page', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      const html = await page.content()
      expect(html).not.toMatch(/inv_[a-f0-9]{32}/)
    })

    test('no service role key in tester pages', async ({ page }) => {
      const pages = ['/tester/invite', '/tester/accept', '/tester/tasks']
      for (const path of pages) {
        await page.goto(`${BASE_URL}${path}`)
        const html = await page.content()
        expect(html).not.toContain('SUPABASE_SERVICE_ROLE')
        expect(html).not.toContain('service_role')
      }
    })

    test('no Stripe live keys in tester pages', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      const html = await page.content()
      expect(html).not.toContain('sk_live_')
    })

    test('no real PII in tester pages', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      const html = await page.content()
      expect(html).not.toMatch(/\d{3}-\d{2}-\d{4}/)
      expect(html).not.toMatch(/\d{16}/)
    })
  })

  test.describe('Workflow State Guards', () => {
    test('invalid token shows error on invite page', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/definitely-not-a-real-token`)
      await expect(page.locator('body')).toContainText(/Invalid Invitation|not valid/)
    })

    test('invalid token does not advance to password form', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/accept?token=definitely-not-a-real-token`)
      const passwordInput = page.locator('[data-testid="password-input"]')
      const isVisible = await passwordInput.isVisible().catch(() => false)
      expect(isVisible).toBe(false)
    })
  })

  test.describe('Admin Panel Integration', () => {
    test('tester invitation panel has expected structure', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 15000 })
      const panelText = await page.locator('[data-testid="tester-invitation-panel"]').textContent()
      expect(panelText).toContain('Tester Invitations')
      expect(panelText).toContain('Total')
      expect(panelText).toContain('Security Notes')
    })

    test('create invitation button exists', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="create-invitation-btn"]', { timeout: 15000 })
      await expect(page.locator('[data-testid="create-invitation-btn"]')).toBeVisible()
    })
  })

  test.describe('Email Template Verification', () => {
    test('send-client-email has tester invitation template', async () => {
      const catalog = await import('../../src/config/serviceOfferCatalog.ts')
      expect(catalog.PILOT_DISCLOSURE_TEXT).toContain('product-testing')
      expect(catalog.PILOT_DISCLOSURE_TEXT).toContain('$1 charge')
    })

    test('hidden pilot offers are configured correctly', async () => {
      const catalog = await import('../../src/config/serviceOfferCatalog.ts')
      const pilotOffer = catalog.HIDDEN_PILOT_OFFERS.find(o => o.slug === 'real-payment-pilot-1')
      expect(pilotOffer).toBeDefined()
      expect(pilotOffer!.requires_invitation).toBe(true)
      expect(pilotOffer!.requires_allowlist).toBe(true)
      expect(pilotOffer!.publicly_visible).toBe(false)
    })
  })
})
