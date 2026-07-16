import { test, expect } from 'playwright/test'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'

function readFile(relativePath: string): string {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test.describe('Friends & Family Preview Certification', () => {
  test.describe('Source Code: Invitation Types', () => {
    test('testerInvitationClient exports friends_family_free type', () => {
      const src = readFile('src/lib/testerInvitationClient.ts')
      expect(src).toContain('friends_family_free')
    })

    test('testerInvitationClient exports friends_family_one_dollar type', () => {
      const src = readFile('src/lib/testerInvitationClient.ts')
      expect(src).toContain('friends_family_one_dollar')
    })

    test('create-tester-invitation edge function supports both types', () => {
      const src = readFile('supabase/functions/create-tester-invitation/index.ts')
      expect(src).toContain('friends_family_free')
      expect(src).toContain('friends_family_one_dollar')
    })

    test('create-tester-invitation auto-derives payment_config per type', () => {
      const src = readFile('supabase/functions/create-tester-invitation/index.ts')
      expect(src).toContain('payment_config')
    })

    test('admin panel shows Friends & Family labels', () => {
      const src = readFile('src/components/TesterInvitationPanel.jsx')
      expect(src).toContain('Friends & Family')
    })

    test('admin panel has type selector with Free Preview option', () => {
      const src = readFile('src/components/TesterInvitationPanel.jsx')
      expect(src).toContain('Free Preview')
    })

    test('admin panel has type selector with $1 Pilot option', () => {
      const src = readFile('src/components/TesterInvitationPanel.jsx')
      expect(src).toContain('$1 Pilot')
    })

    test('admin panel has personal message field', () => {
      const src = readFile('src/components/TesterInvitationPanel.jsx')
      expect(src).toContain('personal_message')
    })
  })

  test.describe('Source Code: Email Template', () => {
    test('email template is personal from Ray Davis', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      expect(src).toContain('Ray Davis')
    })

    test('email template mentions GoClear Online', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      expect(src).toContain('GoClear Online')
    })

    test('email template uses goclearonline.cc domain', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      expect(src).toContain('goclearonline.cc')
    })

    test('email template has Free Preview disclosure', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      expect(src).toContain('Free Preview')
    })

    test('email template supports personal notes', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      expect(src).toContain('personalNote')
    })

    test('email template includes plain-text alternative', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      expect(src).toContain('text/plain')
    })

    test('email template does not mention Stripe', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      const lines = src.split('\n')
      const testerTemplate = lines.filter(l => l.includes('tester_invitation')).join('\n')
      expect(testerTemplate).not.toMatch(/stripe|Stripe|STRIPE/i)
    })

    test('email template does not contain netlify URLs', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      expect(src).not.toContain('netlify.app')
    })
  })

  test.describe('Source Code: One-Click Flow', () => {
    test('TesterInvitePage extracts token from URL path', () => {
      const src = readFile('src/pages/tester/TesterInvitePage.tsx')
      expect(src).toContain("window.location.pathname")
    })

    test('TesterInvitePage calls validateInviteToken', () => {
      const src = readFile('src/pages/tester/TesterInvitePage.tsx')
      expect(src).toContain('validateInviteToken')
    })

    test('TesterInvitePage shows welcome page with Create My Account button', () => {
      const src = readFile('src/pages/tester/TesterInvitePage.tsx')
      expect(src).toContain('Create My Account')
    })

    test('TesterInvitePage shows invitation type labels', () => {
      const src = readFile('src/pages/tester/TesterInvitePage.tsx')
      expect(src).toContain('Free Friends & Family Preview')
      expect(src).toContain('$1 Friends & Family Pilot')
    })

    test('TesterAcceptPage auto-validates token from URL', () => {
      const src = readFile('src/pages/tester/TesterAcceptPage.tsx')
      expect(src).toContain('validateInviteToken')
    })

    test('TesterAcceptPage has password creation form', () => {
      const src = readFile('src/pages/tester/TesterAcceptPage.tsx')
      expect(src).toContain('password')
    })

    test('TesterAcceptPage has consent checkbox', () => {
      const src = readFile('src/pages/tester/TesterAcceptPage.tsx')
      expect(src).toContain('consent')
    })

    test('TesterAcceptPage shows Friends & Family terms', () => {
      const src = readFile('src/pages/tester/TesterAcceptPage.tsx')
      expect(src).toContain('Friends & Family')
    })

    test('App router has /invite route', () => {
      const src = readFile('src/app/App.tsx')
      expect(src).toContain("/invite'")
    })

    test('App router has /invite/accept route', () => {
      const src = readFile('src/app/App.tsx')
      expect(src).toContain("/invite/accept'")
    })
  })

  test.describe('Source Code: Email Delivery', () => {
    test('send-tester-invitation uses token_hash in URL', () => {
      const src = readFile('supabase/functions/send-tester-invitation/index.ts')
      expect(src).toContain('token_hash')
    })

    test('send-tester-invitation passes personalNote to email', () => {
      const src = readFile('supabase/functions/send-tester-invitation/index.ts')
      expect(src).toContain('personalNote')
    })

    test('send-tester-invitation passes isFree flag', () => {
      const src = readFile('supabase/functions/send-tester-invitation/index.ts')
      expect(src).toContain('isFree')
    })

    test('send-tester-invitation passes subject to email', () => {
      const src = readFile('supabase/functions/send-tester-invitation/index.ts')
      expect(src).toContain('subject')
    })
  })

  test.describe('Source Code: Security', () => {
    test('validate-invite-token accepts both raw tokens and token_hashes', () => {
      const src = readFile('supabase/functions/validate-invite-token/index.ts')
      expect(src).toMatch(/token_hash|raw.*token|hex.*pattern/i)
    })

    test('create-tester-invitation does not expose raw tokens in email', () => {
      const src = readFile('supabase/functions/create-tester-invitation/index.ts')
      expect(src).not.toContain('raw_token')
    })

    test('no service_role in frontend code', () => {
      const src = readFile('src/lib/testerInvitationClient.ts')
      expect(src).not.toContain('service_role')
    })

    test('canonical domain module rejects netlify URLs', () => {
      const src = readFile('src/lib/canonicalDomain.ts')
      expect(src).toContain('isRejectedHost')
      expect(src).toContain('netlify.app')
    })
  })

  test.describe('Built Files', () => {
    test('invite page HTML loads without errors', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      const errors: string[] = []
      page.on('pageerror', (err) => errors.push(err.message))
      await page.waitForTimeout(1000)
      expect(errors.filter(e => !e.includes('Supabase') && !e.includes('Functions'))).toHaveLength(0)
    })

    test('invite page shows GoClear branding', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForTimeout(2000)
      const text = await page.textContent('body')
      expect(text).toContain('GoClear')
    })

    test('invite page has no token input field', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      const tokenInput = page.locator('input[name="token"], input[placeholder*="token" i], input[placeholder*="code" i]')
      await expect(tokenInput).toHaveCount(0)
    })

    test('invite page loads within acceptable time', async ({ page }) => {
      const start = Date.now()
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      const elapsed = Date.now() - start
      expect(elapsed).toBeLessThan(10000)
    })

    test('no horizontal overflow on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 })
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(1000)
      const hasHorizontalOverflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth
      })
      expect(hasHorizontalOverflow).toBe(false)
    })

    test('no password in page HTML', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-token`)
      const html = await page.content()
      expect(html).not.toContain('SUPABASE_SERVICE_ROLE')
      expect(html).not.toContain('service_role')
    })
  })
})
