import { expect, test } from 'playwright/test'

const email = process.env.E2E_CLIENT_EMAIL || ''
const password = process.env.E2E_CLIENT_PASSWORD || ''
test.skip(!process.env.E2E_ENABLE_AUTHENTICATED || !email || !password, 'Existing authenticated synthetic client credentials required')

test('V2 Support route exposes the real Customer Service boundary', async ({ page }) => {
  await page.goto('/client/login')
  await page.getByLabel(/email/i).fill(email)
  await page.getByLabel(/password/i).fill(password)
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).not.toHaveURL(/\/client-v2\/login$/, { timeout: 20_000 })
  await page.goto('/client-v2/support')
  await expect(page.getByTestId('support-v2')).toBeVisible({ timeout: 20_000 })
  await expect(page.getByTestId('support-v2')).toHaveAttribute('data-real-backend-connected', 'YES')
})
