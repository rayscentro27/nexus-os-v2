import { expect, test, type Page } from 'playwright/test'

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true'
const persona = { email: process.env.E2E_PERSONA_A_EMAIL, password: process.env.E2E_PERSONA_A_PASSWORD }

async function login(page: Page) {
  await page.goto('/client/login')
  await page.getByLabel(/email/i).fill(persona.email!)
  await page.getByLabel(/password/i).fill(persona.password!)
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL(/\/client\/(onboarding|dashboard|documents|credit-profile)/, { timeout: 20_000 })
}

async function noOverflow(page: Page) {
  const result = await page.evaluate(() => ({ html: document.documentElement.scrollWidth - document.documentElement.clientWidth, body: document.body.scrollWidth - document.body.clientWidth }))
  expect(Math.max(result.html, result.body)).toBeLessThanOrEqual(2)
}

test.describe('Experience 2 authenticated client and mobile certification', () => {
  test.skip(!enabled || !persona.email || !persona.password, 'Synthetic client credentials are required.')
  test('first login, guided routes, inline uploads, and responsive layouts', async ({ page }) => {
    await login(page)
    if (page.url().includes('/client/onboarding')) await expect(page.getByRole('heading', { name: /Welcome to GoClear/i })).toBeVisible()
    for (const route of ['/client/dashboard', '/client/credit-profile', '/client/business-setup', '/client/funding-readiness', '/client/documents']) {
      await page.goto(route)
      await expect(page.locator('.v2-app')).toBeVisible({ timeout: 20_000 })
      await noOverflow(page)
    }
    await page.goto('/client/credit-profile')
    await expect(page.getByText(/Upload credit report/i)).toBeVisible()
    await page.goto('/client/business-setup')
    await expect(page.getByText(/Add business document|business document/i).first()).toBeVisible()
    await page.goto('/client/funding-readiness')
    await expect(page.getByText(/Upload readiness evidence/i)).toBeVisible()
  })

  for (const viewport of [{ width: 375, height: 812 }, { width: 390, height: 844 }, { width: 768, height: 1024 }, { width: 1440, height: 900 }]) {
    test(`responsive ${viewport.width}px has no horizontal overflow`, async ({ browser }) => {
      const context = await browser.newContext({ viewport })
      const page = await context.newPage()
      await login(page)
      await page.goto('/client/dashboard')
      await expect(page.locator('.v2-app')).toBeVisible({ timeout: 20_000 })
      await noOverflow(page)
      await context.close()
    })
  }
})
