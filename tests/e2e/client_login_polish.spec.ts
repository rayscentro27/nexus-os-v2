import { expect, test } from '@playwright/test'

for (const route of ['/client/login', '/client-v2/login']) {
  test(`GoClear client login polish — ${route}`, async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(route, { waitUntil: 'commit' })
    await page.getByRole('heading', { name: 'Client Login' }).waitFor()

    await expect(page.getByRole('heading', { name: 'Client Login' })).toBeVisible()
    await expect(page.getByLabel('Email Address')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Forgot password?' })).toBeVisible()

    const loginButton = page.getByRole('button', { name: 'Sign In' })
    await expect(loginButton).toHaveClass(/bg-teal-600/)
    await expect(page.getByLabel('Email Address')).toHaveClass(/bg-slate-50\/60/)

    await page.getByRole('button', { name: 'Forgot password?' }).click()
    await expect(page.getByRole('button', { name: 'Send Reset Link' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Back to sign in' })).toBeVisible()

    await page.setViewportSize({ width: 390, height: 844 })
    await page.reload({ waitUntil: 'commit' })
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
    }))
    expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.viewport + 2)
    await expect(page.getByRole('heading', { name: 'Client Login' })).toBeVisible()
    await page.screenshot({
      path: `reports/client_portal/client-login-${route.slice(1).replaceAll('/', '-')}-390x844.png`,
      fullPage: true,
    })
  })
}
