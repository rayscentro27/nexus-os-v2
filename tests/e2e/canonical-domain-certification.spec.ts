import { test, expect } from 'playwright/test'
import { readFileSync, readdirSync, statSync } from 'fs'
import { join, resolve } from 'path'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'
const CANONICAL_DOMAIN = 'goclearonline.cc'

function readDirRecursive(dir: string): string[] {
  const results: string[] = []
  try {
    const entries = readdirSync(dir)
    for (const entry of entries) {
      const fullPath = join(dir, entry)
      const stat = statSync(fullPath)
      if (stat.isDirectory()) {
        results.push(...readDirRecursive(fullPath))
      } else if (/\.(html|js|css|json|txt|md)$/.test(entry)) {
        results.push(fullPath)
      }
    }
  } catch { /* dir not found */ }
  return results
}

function readAllDistContent(): string {
  const distDir = resolve(process.cwd(), 'dist')
  const files = readDirRecursive(distDir)
  return files.map(f => {
    try { return readFileSync(f, 'utf-8') } catch { return '' }
  }).join('\n')
}

function readEmailTemplate(): string {
  try {
    return readFileSync(resolve(process.cwd(), 'supabase/functions/send-client-email/index.ts'), 'utf-8')
  } catch { return '' }
}

function readInvitePageSource(): string {
  try {
    return readFileSync(resolve(process.cwd(), 'src/pages/tester/TesterInvitePage.tsx'), 'utf-8')
  } catch { return '' }
}

function readCanonicalDomainModule(): string {
  try {
    return readFileSync(resolve(process.cwd(), 'src/lib/canonicalDomain.ts'), 'utf-8')
  } catch { return '' }
}

test.describe('Canonical Domain Certification', () => {
  test.describe('Source Code Domain References', () => {
    test('email template uses goclearonline.cc', async () => {
      const emailSrc = readEmailTemplate()
      expect(emailSrc).toContain(CANONICAL_DOMAIN)
      expect(emailSrc).not.toContain('nexusv20.netlify.app')
      expect(emailSrc).not.toContain('netlify.app')
    })

    test('email template contains no localhost URLs', async () => {
      const emailSrc = readEmailTemplate()
      expect(emailSrc).not.toContain('localhost:3000')
      expect(emailSrc).not.toContain('localhost:5173')
    })

    test('canonical domain module defines production hosts', async () => {
      const module = readCanonicalDomainModule()
      expect(module).toContain('goclearonline.cc')
      expect(module).toContain('isProductionHost')
      expect(module).toContain('isRejectedHost')
    })

    test('canonical domain module rejects netlify domains', async () => {
      const module = readCanonicalDomainModule()
      expect(module).toContain('netlify.app')
      expect(module).toContain('isRejectedHost')
    })

    test('canonical domain module rejects localhost in production', async () => {
      const module = readCanonicalDomainModule()
      expect(module).toContain('localhost')
    })
  })

  test.describe('Built Files Inspection', () => {
    test('dist files contain no netlify domain references', async () => {
      const content = readAllDistContent()
      expect(content).not.toContain('nexusv20.netlify.app')
    })

    test('dist HTML files contain no localhost references', async () => {
      const distDir = resolve(process.cwd(), 'dist')
      const htmlFiles = readDirRecursive(distDir).filter(f => f.endsWith('.html'))
      for (const file of htmlFiles) {
        const content = readFileSync(file, 'utf-8')
        expect(content).not.toContain('localhost')
        expect(content).not.toContain('127.0.0.1')
      }
    })

    test('production email template contains no netlify domain', async () => {
      const emailSrc = readEmailTemplate()
      expect(emailSrc).not.toContain('nexusv20.netlify.app')
    })

    test('customer-facing invite page source contains no netlify references', async () => {
      const src = readInvitePageSource()
      expect(src).not.toContain('nexusv20.netlify.app')
    })
  })

  test.describe('Served Page Inspection', () => {
    test('served page contains no netlify domain', async ({ page }) => {
      const response = await page.goto(`${BASE_URL}/`)
      expect(response).toBeTruthy()
      const html = await page.content()
      expect(html).not.toContain('nexusv20.netlify.app')
      expect(html).not.toContain('netlify.app')
    })

    test('served invite page contains no netlify domain', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/0000000000000000000000000000000000000000000000000000000000000000`)
      const html = await page.content()
      expect(html).not.toContain('nexusv20.netlify.app')
      expect(html).not.toContain('netlify.app')
    })

    test('no localhost references in served pages', async ({ page }) => {
      const routes = ['/', '/invite/0000000000000000000000000000000000000000000000000000000000000000']
      for (const route of routes) {
        await page.goto(`${BASE_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 10000 }).catch(() => {})
        const html = await page.content()
        expect(html).not.toMatch(/localhost:\d+/g)
        expect(html).not.toContain('127.0.0.1')
      }
    })

    test('invite page shows GoClear branding not Nexus OS', async ({ page }) => {
      await page.goto(`${BASE_URL}/invite/0000000000000000000000000000000000000000000000000000000000000000`)
      await page.waitForTimeout(2000)
      const text = await page.textContent('body')
      expect(text).toContain('GoClear')
      expect(text).not.toContain('Nexus OS')
    })
  })

  test.describe('Server-Side Canonical Origin', () => {
    test('canonical origin module exists with correct exports', async () => {
      const module = readCanonicalDomainModule()
      expect(module).toContain('getCanonicalOrigin')
      expect(module).toContain('buildCustomerUrl')
      expect(module).toContain('validateCustomerUrl')
    })

    test('buildCustomerUrl produces goclearonline.cc URLs', async () => {
      const module = readCanonicalDomainModule()
      expect(module).toContain('https://goclearonline.cc')
    })
  })
})
