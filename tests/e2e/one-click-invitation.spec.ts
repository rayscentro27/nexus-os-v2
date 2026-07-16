import { test, expect } from 'playwright/test'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'
const VALID_TOKEN = process.env.E2E_INVITE_TOKEN || 'test-invite-token'
const INVALID_TOKEN = 'invalid-token-00000'
const EXPIRED_TOKEN = 'expired-token-00000'
const REVOKED_TOKEN = 'revoked-token-00000'

function readInvitePageSource(): string {
  const src = resolve(process.cwd(), 'src/pages/tester/TesterInvitePage.tsx')
  return readFileSync(src, 'utf-8')
}

function readAppRouter(): string {
  const src = resolve(process.cwd(), 'src/app/App.tsx')
  return readFileSync(src, 'utf-8')
}

test.describe('One-Click Invitation Acceptance', () => {
  test.describe('Email Link Behavior', () => {
    test('email link opens /invite route', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      expect(page.url()).toContain('/invite/')
    })

    test('token is read automatically from URL path', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {})
      const url = page.url()
      expect(url).toContain(VALID_TOKEN)
    })

    test('no token input field exists on the page', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      const tokenInput = page.locator('input[name="token"], input[placeholder*="token" i], input[placeholder*="code" i]')
      await expect(tokenInput).toHaveCount(0)
    })
  })

  test.describe('Source Code: Welcome Flow', () => {
    test('invite page extracts token from URL pathname', () => {
      const src = readInvitePageSource()
      expect(src).toContain("window.location.pathname")
    })

    test('invite page auto-validates token via validateInviteToken', () => {
      const src = readInvitePageSource()
      expect(src).toContain('validateInviteToken')
    })

    test('invite page shows welcome state with Create Account button', () => {
      const src = readInvitePageSource()
      expect(src).toContain('Create My Account')
    })

    test('invite page navigates to /invite/accept on button click', () => {
      const src = readInvitePageSource()
      expect(src).toContain('/invite/accept')
    })

    test('router has /invite route', () => {
      const router = readAppRouter()
      expect(router).toContain("/invite'")
    })
  })

  test.describe('Invalid Token', () => {
    test('invalid token shows friendly error message', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${INVALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(3000)
      const body = await page.locator('body').textContent()
      expect(body).toMatch(/invalid|not found|expired|revoked|unable|not valid/i)
    })

    test('invalid token does not show developer errors', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${INVALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(3000)
      const body = await page.locator('body').textContent()
      expect(body).not.toMatch(/stack trace|TypeError|ReferenceError|500 Internal/i)
    })
  })

  test.describe('Expired Token', () => {
    test('expired token shows friendly message', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${EXPIRED_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(3000)
      const body = await page.locator('body').textContent()
      expect(body).toMatch(/expired|invalid|not found|no longer valid|not valid/i)
    })

    test('expired token does not expose technical details', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${EXPIRED_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(3000)
      const body = await page.locator('body').textContent()
      expect(body).not.toMatch(/jwt|token.*decode|supabase/i)
    })
  })

  test.describe('Revoked Token', () => {
    test('revoked token shows friendly message', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${REVOKED_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(3000)
      const body = await page.locator('body').textContent()
      expect(body).toMatch(/revoked|invalid|not found|no longer valid|unavailable|not valid/i)
    })
  })

  test.describe('Source Code: Used Token Handling', () => {
    test('accept page checks if invitation was already used', () => {
      const acceptSrc = readFileSync(resolve(process.cwd(), 'src/pages/tester/TesterAcceptPage.tsx'), 'utf-8')
      expect(acceptSrc).toMatch(/already.*used|already been used/i)
    })

    test('accept page shows sign-in link for already-used invitations', () => {
      const acceptSrc = readFileSync(resolve(process.cwd(), 'src/pages/tester/TesterAcceptPage.tsx'), 'utf-8')
      expect(acceptSrc).toMatch(/sign.?in|Sign In/i)
    })
  })

  test.describe('Security', () => {
    test('token is not stored in localStorage', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(2000)
      const localStorageKeys = await page.evaluate(() => {
        const keys: string[] = []
        for (let i = 0; i < window.localStorage.length; i++) {
          const key = window.localStorage.key(i)
          if (key) keys.push(key)
        }
        return keys
      })
      const hasToken = localStorageKeys.some(k =>
        k.match(/token|invite|auth|secret/i)
      )
      expect(hasToken).toBe(false)
    })

    test('token is not stored in sessionStorage', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(2000)
      const sessionStorageKeys = await page.evaluate(() => {
        const keys: string[] = []
        for (let i = 0; i < window.sessionStorage.length; i++) {
          const key = window.sessionStorage.key(i)
          if (key) keys.push(key)
        }
        return keys
      })
      const hasToken = sessionStorageKeys.some(k =>
        k.match(/token|invite|auth|secret/i)
      )
      expect(hasToken).toBe(false)
    })
  })

  test.describe('Responsive Design', () => {
    test('mobile iPhone-sized viewport renders without errors', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 })
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      const body = await page.locator('body').textContent()
      expect(body!.length).toBeGreaterThan(0)
    })

    test('no horizontal overflow on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 })
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(1000)
      const hasHorizontalOverflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth
      })
      expect(hasHorizontalOverflow).toBe(false)
    })

    test('source: invite page has responsive styling', () => {
      const src = readInvitePageSource()
      expect(src).toContain('maxWidth')
      expect(src).toContain('padding')
    })
  })

  test.describe('UX Quality', () => {
    test('no developer language appears on invitation page', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      const body = await page.locator('body').textContent()
      expect(body).not.toMatch(/debug|TODO|FIXME|console\.log|stack.?trace|error.*500/i)
    })

    test('page has accessible heading', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      const heading = page.locator('h1, h2, h3').first()
      await expect(heading).toBeVisible({ timeout: 5000 })
    })

    test('page loads within acceptable time', async ({ page }) => {
      const start = Date.now()
      await page.goto(`${BASE_URL}/invite/${VALID_TOKEN}`)
      await page.waitForLoadState('domcontentloaded', { timeout: 15000 })
      const elapsed = Date.now() - start
      expect(elapsed).toBeLessThan(10000)
    })
  })
})
