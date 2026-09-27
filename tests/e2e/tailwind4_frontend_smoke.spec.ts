import { test, expect } from '@playwright/test'

test('public front page remains functional on the Tailwind 4 foundation', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.goto('/', { waitUntil: 'commit' })
  await expect(page.getByText('Stronger Business.', { exact: false })).toBeVisible({ timeout: 15_000 })
  await expect(page.getByRole('link', { name: /Login/i })).toBeVisible()
  await expect(page.getByRole('link', { name: /Sign Up/i })).toBeVisible()
  await page.screenshot({ path: 'reports/client_portal/tailwind4-migration/front-page-desktop-1440x900.png', fullPage: false })
  expect(errors).toEqual([])
})
