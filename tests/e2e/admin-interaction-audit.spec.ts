import { expect, test } from 'playwright/test'

const routes = ['live-intelligence', 'ai-command', 'projects', 'tasks', 'research', 'knowledge', 'analytics', 'automation', 'campaigns', 'decisions', 'departments', 'trading', 'settings', 'support']

test.describe('canonical Admin interaction contract', () => {
  test('canonical controls have destinations, handlers, or explicit disabled state', async ({ page }) => {
    for (const route of routes) {
      await page.goto(`http://127.0.0.1:5174/admin?ui-smoke=1#/${route}`)
      await expect(page.locator('.live-command-page')).toBeVisible()
      const audit = await page.locator('.live-command-page').evaluate((root) => {
        const interactive = [...root.querySelectorAll('a, button, input')]
        const visible = (element: Element) => {
          const style = getComputedStyle(element)
          return style.display !== 'none' && style.visibility !== 'hidden'
        }
        const legacy = ['Live Intelligence', 'Work', 'Agents', 'Business', 'Studio', 'Trading Lab', 'Access & Comms']
        return {
          emptyHash: interactive.filter(element => visible(element) && element.tagName === 'A' && (element as HTMLAnchorElement).getAttribute('href') === '#').map(element => element.outerHTML),
          silentButtons: interactive.filter(element => visible(element) && element.tagName === 'BUTTON' && !(element as HTMLButtonElement).disabled && !element.textContent?.trim() && !element.getAttribute('aria-label')).map(element => element.outerHTML),
          legacyLabels: legacy.filter(label => root.textContent?.includes(label)),
          shellCount: [root.querySelectorAll('.live-command-sidebar').length, root.querySelectorAll('.live-command-topbar').length, root.querySelectorAll('.live-command-main').length],
        }
      })
      expect(audit.emptyHash, route).toEqual([])
      expect(audit.silentButtons, route).toEqual([])
      expect(audit.legacyLabels, route).toEqual([])
      expect(audit.shellCount, route).toEqual([1, 1, 1])
    }
  })

  test('dashboard navigation resolves to canonical routes and unavailable writes are explicit', async ({ page }) => {
    await page.goto('http://127.0.0.1:5174/admin?ui-smoke=1#/live-intelligence')
    await expect(page.getByRole('link', { name: 'Explore intelligence' })).toHaveAttribute('href', '#/research')
    await expect(page.getByRole('link', { name: 'Ask AI' })).toHaveAttribute('href', '#/ai-command')
    await expect(page.getByRole('link', { name: 'Research Market' })).toHaveAttribute('href', '#/research')
    await expect(page.getByRole('link', { name: 'View all' }).first()).toHaveAttribute('href', '#/knowledge')
    await expect(page.locator('button[disabled][title*="NOT_YET_AVAILABLE"]').first()).toBeVisible()
  })
})
