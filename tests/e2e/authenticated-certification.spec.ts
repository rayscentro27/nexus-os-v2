import { expect, test } from 'playwright/test'

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true'
const email = process.env.E2E_PERSONA_A_EMAIL
const password = process.env.E2E_PERSONA_A_PASSWORD

test.describe('synthetic authenticated client certification', () => {
  test.skip(!enabled || !email || !password, 'Set E2E_ENABLE_AUTHENTICATED=true and local synthetic persona credentials; credentials are never stored in Git.')
  test('client session persists and cannot access admin routes', async ({ page }) => {
    await page.goto('/client/login')
    await page.getByLabel(/email/i).fill(email!)
    await page.getByLabel(/password/i).fill(password!)
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 15_000 })
    await expect(page).not.toHaveURL(/\/client\/login/)
    await page.goto('/admin/credit-specialist')
    await expect(page.getByRole('heading', { name: /admin access required/i })).toBeVisible()
    await expect(page.getByText(/does not have admin access/i)).toBeVisible()
  })
})
