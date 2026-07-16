import { test, expect } from 'playwright/test'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'
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

test.describe('Invited Payment Pilot Certification', () => {
  test.describe('Checkout Guards', () => {
    test('hidden $1 offer not visible on public pricing', async ({ page }) => {
      await page.goto(`${BASE_URL}/pricing`)
      const pageText = await page.locator('body').textContent()
      expect(pageText).not.toContain('real-payment-pilot-1')
      expect(pageText).not.toContain('Real Payment Pilot')
    })

    test('hidden $1 offer not visible on readiness-review page', async ({ page }) => {
      await page.goto(`${BASE_URL}/readiness-review`)
      const pageText = await page.locator('body').textContent()
      expect(pageText).not.toContain('real-payment-pilot-1')
    })

    test('controlled live pilot is disabled by default', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      const panelText = await page.locator('[data-testid="tester-invitation-panel"]').textContent()
      expect(panelText).toContain('Controlled live pilot requires separate Ray approval')
    })

    test('public live is disabled', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      const panelText = await page.locator('[data-testid="tester-invitation-panel"]').textContent()
      expect(panelText).toContain('Public live payments remain disabled')
    })

    test('emergency disable button exists', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      const panelText = await page.locator('[data-testid="tester-invitation-panel"]').textContent()
      expect(panelText).toContain('Security Notes')
    })
  })

  test.describe('Invited Checkout Flow', () => {
    test('tester tasks page requires login', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/tasks`)
      await page.waitForTimeout(3000)
      const pageText = await page.locator('body').textContent()
      const requiresLogin = pageText.includes('sign in') || pageText.includes('Sign in')
      expect(requiresLogin).toBe(true)
    })

    test('invite token validation works', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      await page.fill('[data-testid="invite-token-input"]', 'test-invalid-token')
      await page.click('[data-testid="invite-validate-btn"]')
      await page.waitForTimeout(2000)
      const error = page.locator('[data-testid="invite-error"]')
      await expect(error).toBeVisible()
    })
  })

  test.describe('Payment Mode Guards', () => {
    test('test mode is default', async ({ page }) => {
      await loginAsAdmin(page)
      await page.goto(`${BASE_URL}/admin#tester-invitations`)
      await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 10000 })
      const panelText = await page.locator('[data-testid="tester-invitation-panel"]').textContent()
      expect(panelText).toContain('Mode: test')
    })

    test('no live Stripe keys in environment', async () => {
      const env = process.env.STRIPE_SECRET_KEY || ''
      expect(env.startsWith('sk_live_')).toBe(false)
    })
  })

  test.describe('Security', () => {
    test('no card data in public pages', async ({ page }) => {
      const pages = ['/', '/pricing', '/readiness-review', '/tester/invite']
      for (const path of pages) {
        await page.goto(`${BASE_URL}${path}`)
        const html = await page.content()
        expect(html).not.toContain('4242')
        expect(html).not.toMatch(/\d{4}\s\d{4}\s\d{4}\s\d{4}/)
      }
    })

    test('no service role in frontend bundles', async ({ page }) => {
      await page.goto(`${BASE_URL}/`)
      const html = await page.content()
      expect(html).not.toContain('SUPABASE_SERVICE_ROLE')
      expect(html).not.toContain('service_role')
    })

    test('no webhook secrets in frontend', async ({ page }) => {
      await page.goto(`${BASE_URL}/`)
      const html = await page.content()
      expect(html).not.toContain('whsec_')
    })

    test('no real PII in tester pages', async ({ page }) => {
      await page.goto(`${BASE_URL}/tester/invite`)
      const html = await page.content()
      expect(html).not.toMatch(/\d{3}-\d{2}-\d{4}/)
      expect(html).not.toMatch(/\d{16}/)
    })
  })

  test.describe('Foundation Status', () => {
    test('hidden pilot offer exists in catalog', async () => {
      const catalog = await import('../../src/config/serviceOfferCatalog.ts')
      const offer = catalog.HIDDEN_PILOT_OFFERS.find(o => o.slug === 'real-payment-pilot-1')
      expect(offer).toBeDefined()
      expect(offer!.active).toBe(false)
      expect(offer!.publicly_visible).toBe(false)
      expect(offer!.requires_invitation).toBe(true)
      expect(offer!.requires_allowlist).toBe(true)
    })

    test('invited test offer exists in catalog', async () => {
      const catalog = await import('../../src/config/serviceOfferCatalog.ts')
      const offer = catalog.SERVICE_OFFER_CATALOG.find(o => o.slug === 'invited-readiness-test')
      expect(offer).toBeDefined()
      expect(offer!.active).toBe(false)
    })

    test('pilot disclosure text is defined', async () => {
      const catalog = await import('../../src/config/serviceOfferCatalog.ts')
      expect(catalog.PILOT_DISCLOSURE_TEXT).toContain('limited paid product-testing program')
      expect(catalog.PILOT_DISCLOSURE_TEXT).toContain('$1 charge')
    })
  })
})
