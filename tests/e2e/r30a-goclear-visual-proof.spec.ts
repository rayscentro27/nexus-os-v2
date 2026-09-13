import { expect, test } from 'playwright/test'

const email = process.env.E2E_CLIENT_EMAIL || ''
const password = process.env.E2E_CLIENT_PASSWORD || ''
test.skip(!process.env.E2E_ENABLE_AUTHENTICATED || !email || !password, 'Existing authenticated synthetic client credentials required')

async function login(page: import('playwright/test').Page) {
  await page.goto('/client/login')
  await page.getByLabel(/email/i).fill(email)
  await page.getByLabel(/password/i).fill(password)
  await page.getByRole('button', { name: /sign in/i }).click()
  // The existing client auth flow intentionally lands in profile intake.
  // Authenticated V2 proof starts from the protected V2 route after the
  // session is established; it must not depend on onboarding completion.
  await expect(page).not.toHaveURL(/\/client\/login$/, { timeout: 20_000 })
}

test.describe('GoClear Client Portal V2 approved visual system', () => {
  for (const [name, width, height] of [['desktop', 1440, 900], ['tablet', 820, 1180], ['mobile', 390, 844]] as const) {
    test(`${name} authenticated visual routes use live V2 shell`, async ({ page }) => {
      await page.setViewportSize({ width, height })
      await login(page)
      for (const [route, slug] of [['/client-v2/dashboard', 'dashboard'], ['/client-v2/funding-readiness', 'funding'], ['/client-v2/goals', 'goals'], ['/client-v2/documents', 'documents']] as const) {
        await page.goto(route)
        await expect(page.locator('.v2-app')).toBeVisible({ timeout: 20_000 })
        await expect(page).not.toHaveURL(/\/client-v2\/login$/)
        await expect(page.getByText('Live data')).toBeVisible({ timeout: 20_000 })
        await page.screenshot({ path: `test-results/r30a-goclear-${name}-${slug}.png`, fullPage: true })
      }
    })
  }
})
