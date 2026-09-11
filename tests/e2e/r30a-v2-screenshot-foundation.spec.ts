import { test } from 'playwright/test'

test('R30A captures design-neutral V2 viewport artifacts', async ({ page }) => {
  for (const [name, width, height] of [['desktop', 1440, 900], ['tablet', 820, 1180], ['mobile', 390, 844]] as const) {
    await page.setViewportSize({ width, height })
    await page.goto('/client-v2/login')
    await page.screenshot({ path: `test-results/r30a-v2-${name}.png`, fullPage: true })
  }
})
