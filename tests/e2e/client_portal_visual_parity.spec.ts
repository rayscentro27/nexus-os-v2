import { test, expect } from '@playwright/test'

const viewportCases = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 },
]

for (const viewportCase of viewportCases) {
  test(`GoClear approved portal visual structure — ${viewportCase.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewportCase.width, height: viewportCase.height })
    await page.goto('/client/preview', { waitUntil: 'commit' })
    await page.waitForTimeout(800)

    const portal = page.locator('.goclear-approved-portal')
    await portal.waitFor({ state: 'attached', timeout: 15_000 })
    await expect(portal).toHaveAttribute('data-visual-source', 'google-ai-studio-approved')
    await expect(page.locator('text=Funding Readiness Command')).toBeVisible()

    await page.screenshot({
      path: `reports/client_portal/tailwind4-migration/client-preview-${viewportCase.name}-${viewportCase.width}x${viewportCase.height}.png`,
      fullPage: false,
    })

    if (viewportCase.name === 'desktop') {
      const metrics = await page.evaluate(() => {
        const rect = (selector: string) => {
          const element = document.querySelector(selector)
          if (!element) return null
          const box = element.getBoundingClientRect()
          const styles = getComputedStyle(element)
          return {
            x: box.x, y: box.y, width: box.width, height: box.height,
            display: styles.display, grid: styles.gridTemplateColumns,
            padding: styles.padding, margin: styles.margin, gap: styles.gap,
            fontSize: styles.fontSize, fontWeight: styles.fontWeight,
            lineHeight: styles.lineHeight, background: styles.backgroundColor,
            color: styles.color, border: styles.border, radius: styles.borderRadius,
            shadow: styles.boxShadow, opacity: styles.opacity,
          }
        }
        const journey = [...document.querySelectorAll('.grid')].find((element) => element.className.includes('grid-cols-7'))
        const missions = [...document.querySelectorAll('.grid')].find((element) => element.className.includes('sm:grid-cols-2'))
        return {
          sidebar: rect('aside'),
          command: rect('h1'),
          journey: journey ? { display: getComputedStyle(journey).display, grid: getComputedStyle(journey).gridTemplateColumns } : null,
          missions: missions ? { display: getComputedStyle(missions).display, grid: getComputedStyle(missions).gridTemplateColumns } : null,
          momentum: [...document.querySelectorAll('h2')].some((node) => node.textContent?.includes('Momentum')),
          footer: rect('footer'),
        }
      })
      expect(metrics.sidebar?.display).toBe('flex')
      expect(metrics.sidebar?.width).toBe(272)
      expect(metrics.sidebar?.padding).toBe('0px')
      expect(metrics.journey?.grid.split(' ').length).toBe(7)
      expect(metrics.journey?.display).toBe('grid')
      expect(metrics.missions?.grid.split(' ').length).toBe(2)
      expect(metrics.missions?.display).toBe('grid')
      expect(metrics.momentum).toBeTruthy()
      expect(metrics.footer?.display).toBe('flex')
      expect(metrics.footer?.height).toBe(28)
      expect(metrics.command?.fontSize).toBe('16px')
      expect(metrics.command?.fontWeight).toBe('700')
    } else {
      await expect(page.locator('aside')).toBeHidden()
      await expect(page.getByRole('navigation', { name: 'Mobile Navigation Dock' })).toBeVisible()
    }
  })
}
