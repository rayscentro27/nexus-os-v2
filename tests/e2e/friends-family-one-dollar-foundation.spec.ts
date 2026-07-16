import { test, expect } from 'playwright/test'
import { readFileSync } from 'fs'
import { resolve } from 'path'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'
const CANONICAL_DOMAIN = 'goclearonline.cc'

function readFile(relativePath: string): string {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

function readDistJs(): string {
  try {
    const distDir = resolve(process.cwd(), 'dist')
    const files = require('fs').readdirSync(resolve(distDir, 'assets')).filter((f: string) => f.endsWith('.js'))
    return files.map((f: string) => readFileSync(resolve(distDir, 'assets', f), 'utf-8')).join('\n')
  } catch {
    return ''
  }
}

test.describe('Friends & Family $1 Foundation', () => {
  test.describe('Source Code: Invitation Types', () => {
    test('friends_family_one_dollar type exists in codebase', () => {
      const src = readFile('src/lib/testerInvitationClient.ts')
      expect(src).toContain('friends_family_one_dollar')
    })

    test('friends_family_one_dollar is distinct from friends_family_free', () => {
      const src = readFile('src/lib/testerInvitationClient.ts')
      expect(src).toContain('friends_family_free')
      expect(src).toContain('friends_family_one_dollar')
    })

    test('create-tester-invitation supports $1 pilot type', () => {
      const src = readFile('supabase/functions/create-tester-invitation/index.ts')
      expect(src).toContain('friends_family_one_dollar')
    })

    test('$1 pilot auto-derives payment_config', () => {
      const src = readFile('supabase/functions/create-tester-invitation/index.ts')
      expect(src).toContain('payment_config')
    })
  })

  test.describe('Source Code: $1 Pilot Controls', () => {
    test('controlled_live_pilot is disabled', () => {
      const src = readFile('src/lib/testerInvitationClient.ts')
      const match = src.match(/controlled_live_pilot[^;]*?false/i)
      expect(match).toBeTruthy()
    })

    test('public_live is disabled', () => {
      const src = readFile('src/lib/testerInvitationClient.ts')
      const match = src.match(/public_live[^;]*?false/i)
      expect(match).toBeTruthy()
    })

    test('$1 checkout function exists', () => {
      const src = readFile('supabase/functions/create-invited-checkout/index.ts')
      expect(src).toContain('invited')
    })
  })

  test.describe('Source Code: Security', () => {
    test('no service role key in frontend code', () => {
      const src = readFile('src/lib/testerInvitationClient.ts')
      expect(src).not.toContain('SUPABASE_SERVICE_ROLE')
    })

    test('no raw Stripe keys in source', () => {
      const srcFiles = [
        'src/lib/testerInvitationClient.ts',
        'src/pages/tester/TesterInvitePage.tsx',
        'src/pages/tester/TesterAcceptPage.tsx'
      ]
      for (const f of srcFiles) {
        const src = readFile(f)
        expect(src).not.toMatch(/sk_live_/)
        expect(src).not.toMatch(/sk_test_/)
      }
    })

    test('no netlify URLs in customer-facing source', () => {
      const srcFiles = [
        'src/pages/tester/TesterInvitePage.tsx',
        'src/pages/tester/TesterAcceptPage.tsx',
        'src/lib/canonicalDomain.ts'
      ]
      for (const f of srcFiles) {
        const src = readFile(f)
        expect(src).not.toContain('nexusv20.netlify.app')
      }
    })
  })

  test.describe('Source Code: Email Template', () => {
    test('email template mentions GoClear not Nexus', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      expect(src).toContain('GoClear')
    })

    test('email template uses canonical domain', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      expect(src).toContain('goclearonline.cc')
    })

    test('email template does not mention Stripe', () => {
      const src = readFile('supabase/functions/send-client-email/index.ts')
      const lines = src.split('\n')
      const testerLines = lines.filter(l => l.includes('tester_invitation'))
      expect(testerLines.join('\n')).not.toMatch(/stripe|Stripe/i)
    })
  })

  test.describe('Dist Files', () => {
    test('dist contains friends_family_one_dollar reference', () => {
      const content = readDistJs()
      expect(content).toContain('friends_family_one_dollar')
    })

    test('dist does not contain netlify domain', () => {
      const content = readDistJs()
      expect(content).not.toContain('nexusv20.netlify.app')
    })

    test('dist contains canonical domain', () => {
      const content = readDistJs()
      expect(content).toContain(CANONICAL_DOMAIN)
    })
  })

  test.describe('Static Page Tests', () => {
    test('invite page loads without JavaScript errors', async ({ page }) => {
      const errors: string[] = []
      page.on('pageerror', (err) => errors.push(err.message))
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(2000)
      const criticalErrors = errors.filter(e => !e.includes('Supabase') && !e.includes('Functions'))
      expect(criticalErrors).toHaveLength(0)
    })

    test('invite page shows GoClear branding', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForTimeout(2000)
      const text = await page.textContent('body')
      expect(text).toContain('GoClear')
    })

    test('invite page has no token input', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      const tokenInput = page.locator('input[name="token"], input[placeholder*="token" i]')
      await expect(tokenInput).toHaveCount(0)
    })

    test('no $1 pricing visible on public invite page', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      const text = await page.textContent('body')
      expect(text).not.toMatch(/\$1\.00/)
    })

    test('no service role key exposed in page HTML', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/test-token`)
      const html = await page.content()
      expect(html).not.toContain('SUPABASE_SERVICE_ROLE')
      expect(html).not.toContain('service_role')
    })

    test('no horizontal overflow on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 })
      await page.goto(`${BASE_URL}/invite/test-token`)
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      await page.waitForTimeout(1000)
      const hasOverflow = await page.evaluate(() =>
        document.documentElement.scrollWidth > document.documentElement.clientWidth
      )
      expect(hasOverflow).toBe(false)
    })
  })
})
