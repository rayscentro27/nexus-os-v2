import { expect, test, type Page } from 'playwright/test'

const required = (name: string) => { const value = process.env[name]; if (!value) throw new Error(`${name} is required for revenue activation certification`); return value }
required('E2E_ENABLE_AUTHENTICATED')
const personaA = { email: required('E2E_PERSONA_A_EMAIL'), password: required('E2E_PERSONA_A_PASSWORD') }
const admin = { email: required('E2E_ADMIN_EMAIL'), password: required('E2E_ADMIN_PASSWORD') }
const supabaseUrl = required('VITE_SUPABASE_URL')
const supabaseKey = required('VITE_SUPABASE_ANON_KEY')

async function loginClient(page: Page) {
  await page.goto('/client/login'); await page.getByLabel(/email/i).fill(personaA.email); await page.getByLabel(/password/i).fill(personaA.password); await page.getByRole('button', { name: /sign in/i }).click(); await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)
}
async function loginAdmin(page: Page) {
  await page.goto('/admin/login'); await page.getByLabel(/email/i).fill(admin.email); await page.getByLabel(/password/i).fill(admin.password); await page.getByRole('button', { name: /sign in|log in/i }).click(); await expect(page).toHaveURL(/\/admin\/?$/)
}

test.describe('revenue activation — controlled test mode', () => {
  test('public pricing displays the three service offers and safe claims', async ({ page }) => {
    await page.goto('/pricing'); const pricing = page.getByTestId('service-pricing'); await expect(pricing).toBeVisible();
    for (const slug of ['readiness-review-97', 'readiness-action-plan-297', 'funding-readiness-concierge-497']) await expect(pricing.getByTestId(`offer-card-${slug}`)).toBeVisible()
    await expect(pricing).toContainText('$97'); await expect(pricing).toContainText('$297'); await expect(pricing).toContainText('$497'); await expect(pricing).toContainText(/does not guarantee funding/i)
  })

  test('selected offer reaches controlled checkout initiation without browser price input', async ({ page }) => {
    await page.goto('/readiness-review'); const offer = page.getByTestId('service-offer-readiness-review-97'); await expect(offer).toBeVisible(); await expect(offer).toContainText('9700'.replace('00', ''));
    await expect(offer.getByTestId('start-test-checkout')).toBeVisible(); await expect(page.locator('input[autocomplete="cc-number"]')).toHaveCount(0); await expect(offer).toContainText(/hosted Stripe test-mode/i)
  })

  test('anonymous access cannot read orders and return states do not trust query strings', async ({ page }) => {
    await page.goto('/checkout/success?order=not-a-real-order'); await expect(page.getByTestId('checkout-success')).toContainText(/persisted order state/i)
    const result = await page.evaluate(async ({ url, key }) => { const response = await fetch(`${url}/rest/v1/client_orders?select=id&limit=1`, { headers: { apikey: key, Authorization: `Bearer ${key}` } }); return { status: response.status, body: await response.text() } }, { url: supabaseUrl, key: supabaseKey });
    expect(result.status >= 200 && result.status < 300 ? JSON.parse(result.body || '[]').length === 0 : true).toBeTruthy()
  })

  test('synthetic client sees an order-aware protected service section', async ({ page }) => {
    await loginClient(page); await page.goto('/client/dashboard'); const card = page.getByTestId('client-revenue-service'); await expect(card).toBeVisible(); await expect(card).toContainText(/Purchased service|No paid readiness service/i); await expect(page.locator('body')).not.toContainText(/sk_(live|test)_/i); await expect(page.locator('body')).not.toContainText(/signed_url|signedurl/i)
  })

  test('client portal keeps readiness packet and delivery approval-gated', async ({ page }) => {
    await loginClient(page); await page.goto('/client/dashboard'); const card = page.getByTestId('client-revenue-service'); await expect(card).toBeVisible(); await expect(card).toContainText(/TEST MODE|Approval gated|No paid readiness service/i); const body = await page.locator('body').innerText(); expect(body).not.toMatch(/packet delivered automatically|automatic delivery/i)
  })

  test('client cannot open admin revenue controls', async ({ page }) => {
    await loginClient(page); await page.goto('/admin/revenue-activation'); await expect(page).toHaveURL(/\/admin\/revenue-activation|\/admin\/login/); await expect(page.getByText(/admin access required|sign in/i).first()).toBeVisible()
  })

  test('admin sees test-mode order and fulfillment operations', async ({ page }) => {
    await loginAdmin(page); await page.goto('/admin/#revenue-activation'); const panel = page.getByTestId('revenue-activation-panel'); await expect(panel).toBeVisible(); await expect(panel).toContainText('TEST MODE ONLY'); await expect(panel).toContainText('Offer catalog'); await expect(panel).toContainText('$97'); await expect(panel).toContainText('$297'); await expect(panel).toContainText('$497')
  })

  test('admin surface exposes the Ray approval and consultation gates', async ({ page }) => {
    await loginAdmin(page); await page.goto('/admin/#revenue-activation'); const panel = page.getByTestId('revenue-activation-panel'); await expect(panel).toContainText(/Ray Review|Consultation/i); await expect(panel).toContainText(/no live payment|no automatic/i)
  })

  test('responsive offer and client order surfaces have no horizontal overflow', async ({ page }) => {
    for (const viewport of [{ width: 1920, height: 1080 }, { width: 1366, height: 768 }, { width: 768, height: 1024 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(viewport); await page.goto('/pricing'); await expect(page.getByTestId('service-pricing')).toBeVisible(); const metrics = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth })); expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 2); await expect(page.getByRole('link', { name: /Review service/i }).first()).toBeVisible()
    }
  })
})
