import { test, expect, type Page, type Locator } from 'playwright/test'
import { existsSync, readFileSync } from 'fs'
import { resolve } from 'path'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'

function loadLocalE2EEnv() {
  if (process.env.E2E_ADMIN_EMAIL && process.env.E2E_ADMIN_PASSWORD) return
  const envPath = resolve(process.cwd(), '.env.e2e.local')
  if (!existsSync(envPath)) return
  for (const line of readFileSync(envPath, 'utf-8').split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
    const [key, ...valueParts] = trimmed.split('=')
    if (!process.env[key]) process.env[key] = valueParts.join('=')
  }
}

loadLocalE2EEnv()

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || ''
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || ''

function readSrc(relativePath: string): string {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

async function loginAsAdmin(page: Page) {
  await page.goto(`${BASE_URL}/admin/login`)
  await page.waitForLoadState('domcontentloaded', { timeout: 15_000 })
  await page.fill('#admin-email', ADMIN_EMAIL)
  await page.fill('#admin-password', ADMIN_PASSWORD)
  await page.getByRole('button', { name: /sign in/i }).click()
  await page.waitForURL(/\/admin\/?$/, { timeout: 20_000 }).catch(() => {})
  await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
  await page.waitForTimeout(1500)
}

function intersectionArea(a: any, b: any) {
  if (!a || !b) return 0
  const left = Math.max(a.x, b.x)
  const right = Math.min(a.x + a.width, b.x + b.width)
  const top = Math.max(a.y, b.y)
  const bottom = Math.min(a.y + a.height, b.y + b.height)
  return Math.max(0, right - left) * Math.max(0, bottom - top)
}

async function expectNoIntersection(a: Locator, b: Locator) {
  const [boxA, boxB] = await Promise.all([a.boundingBox(), b.boundingBox()])
  expect(intersectionArea(boxA, boxB)).toBe(0)
}

async function routeGeometry(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height })
  await loginAsAdmin(page)
  await page.goto(`${BASE_URL}/admin#tester-invitations`)
  await page.waitForSelector('[data-testid="tester-invitation-panel"]', { timeout: 20_000 })
  await page.waitForTimeout(1000)

  const panel = page.locator('[data-testid="tester-invitation-panel"]')
  const create = page.locator('[data-testid="create-invitation-btn"]')
  const metrics = page.locator('.tester-metric-chips')
  const safety = page.locator('[data-testid="payment-safety-strip"]')
  const table = page.locator('[data-testid="invitation-table-body"]')
  const hermes = page.locator('.hermes-global-launcher')
  const footer = page.locator('.footer')

  await expect(panel).toBeVisible()
  await expect(panel).toContainText('Tester Invitations')
  await expect(create).toBeVisible()
  await expect(metrics).toBeVisible()
  await expect(safety).toBeVisible()
  await expect(table).toBeVisible()
  await expect(page.locator('body')).toContainText('Public live payments remain disabled')

  const overflow = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    panel: (() => {
      const r = document.querySelector('[data-testid="tester-invitation-panel"]')?.getBoundingClientRect()
      return r ? { x: r.x, right: r.right, width: r.width } : null
    })(),
  }))
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1)
  expect(overflow.panel?.x ?? 0).toBeGreaterThanOrEqual(0)
  expect(overflow.panel?.right ?? 0).toBeLessThanOrEqual(width + 1)

  await expectNoIntersection(hermes, panel)
  await expectNoIntersection(footer, panel)

  await create.click()
  const drawer = page.locator('[data-testid="create-invitation-drawer"] .tester-invite-drawer')
  const footerActions = page.locator('[data-testid="create-drawer-footer"]')
  await expect(drawer).toBeVisible()
  await expect(page.locator('[data-testid="new-inv-name"]')).toBeVisible()
  await expect(page.locator('[data-testid="new-inv-email"]')).toBeVisible()
  await expect(footerActions).toBeVisible()
  await expectNoIntersection(hermes, drawer)

  const drawerBox = await drawer.boundingBox()
  expect(drawerBox?.x ?? 0).toBeGreaterThanOrEqual(0)
  expect((drawerBox?.x ?? 0) + (drawerBox?.width ?? 0)).toBeLessThanOrEqual(width + 1)
  expect(drawerBox?.height ?? 0).toBeLessThanOrEqual(height + 1)

  return { drawerBox }
}

test.describe('Tester Invitations Layout Certification', () => {
  test.describe('Source contracts', () => {
    test('compact panel, drawer, safety strip, and email preview are implemented', () => {
      const src = readSrc('src/components/TesterInvitationPanel.jsx')
      expect(src).toContain('tester-invitation-panel')
      expect(src).toContain('tester-metric-chips')
      expect(src).toContain('payment-safety-strip')
      expect(src).toContain('CreateDrawer')
      expect(src).toContain('InvitationEmailPreview')
      expect(src).toContain('goclearonline.cc')
      expect(src).not.toContain('netlify.app')
      expect(src).not.toMatch(/sk_live_|sk_test_|whsec_/)
    })

    test('tester-invitations route has route-scoped layout hooks', () => {
      const src = readSrc('src/admin/NexusAdminUI.jsx')
      expect(src).toContain('tester-invitations-page')
      expect(src).toContain('active-page-')
      const routeLine = src.split('\n').find(line => line.includes("'tester-invitations'")) || ''
      expect(routeLine).not.toContain('SimplePage')
    })
  })

  test.describe('Authenticated geometry', () => {
    test.beforeEach(() => {
      test.skip(!ADMIN_EMAIL || !ADMIN_PASSWORD, 'E2E admin credentials required for authenticated geometry')
    })

    test('desktop 1920x1080 route and drawer geometry', async ({ page }) => {
      await routeGeometry(page, 1920, 1080)
    })

    test('desktop 1440x900 route and drawer geometry', async ({ page }) => {
      await routeGeometry(page, 1440, 900)
    })

    test('desktop 1280x720 route and drawer geometry', async ({ page }) => {
      await routeGeometry(page, 1280, 720)
      const body = page.locator('[data-testid="create-drawer-body"]')
      const scroll = await body.evaluate((el) => ({ scrollHeight: el.scrollHeight, clientHeight: el.clientHeight, overflowY: getComputedStyle(el).overflowY }))
      expect(scroll.overflowY).toBe('auto')
      expect(scroll.scrollHeight).toBeGreaterThanOrEqual(scroll.clientHeight)
    })

    test('iPhone route and full-screen single-column drawer geometry', async ({ page }) => {
      const { drawerBox } = await routeGeometry(page, 390, 844)
      expect(drawerBox?.x ?? -1).toBeLessThanOrEqual(1)
      expect(drawerBox?.width ?? 0).toBeGreaterThanOrEqual(389)

      const sidebarVisible = await page.locator('.sidebar').isVisible().catch(() => false)
      expect(sidebarVisible).toBe(false)

      const [nameBox, emailBox] = await Promise.all([
        page.locator('[data-testid="new-inv-name"]').boundingBox(),
        page.locator('[data-testid="new-inv-email"]').boundingBox(),
      ])
      expect(Math.abs((nameBox?.x ?? 0) - (emailBox?.x ?? 999))).toBeLessThanOrEqual(1)
      expect((emailBox?.y ?? 0)).toBeGreaterThan((nameBox?.y ?? 0))
    })
  })
})
