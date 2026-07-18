import { expect, test, type Browser, type Page } from 'playwright/test'

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true'

const personaA = { label: 'Persona A', email: process.env.E2E_PERSONA_A_EMAIL, password: process.env.E2E_PERSONA_A_PASSWORD }
const personaB = { label: 'Persona B', email: process.env.E2E_PERSONA_B_EMAIL, password: process.env.E2E_PERSONA_B_PASSWORD }
const personaC = { label: 'Persona C', email: process.env.E2E_PERSONA_C_EMAIL, password: process.env.E2E_PERSONA_C_PASSWORD }
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD }

const clientRoutes = [
  ['/client/dashboard', 'wc-panel-home', /Funding Readiness Command Center/i],
  ['/client/credit-profile', 'wc-panel-credit', /Credit Journey/i],
  ['/client/credit-utilization', 'wc-panel-credit', /Credit Utilization/i],
  ['/client/account-details', 'wc-panel-credit', /Account Details|Credit Journey/i],
  ['/client/credit-repair-journey', 'wc-panel-repair', /Credit Repair/i],
  ['/client/business-journey', 'wc-panel-business', /Business Journey/i],
  ['/client/business-setup', 'wc-panel-business', /Business Setup/i],
  ['/client/business-bankability', 'wc-panel-business', /Business Bankability/i],
  ['/client/business-credit', 'wc-panel-business', /Business Credit/i],
  ['/client/documents', 'wc-panel-documents', /Central Document Vault/i],
  ['/client/funding-readiness', 'wc-panel-funding', /Funding Readiness/i],
  ['/client/recommendations', 'wc-panel-recommendations', /Funding Readiness Recommendations/i],
  ['/client/resources', 'wc-panel-resources', /Funding Readiness Resources/i],
  ['/client/request-review', 'wc-panel-review', /Readiness Review/i],
] as const

const viewports = [
  { name: 'desktop', width: 1920, height: 1080 },
  { name: 'laptop', width: 1440, height: 900 },
  { name: 'tablet', width: 1024, height: 768 },
  { name: 'mobile', width: 390, height: 844 },
] as const

async function loginClient(page: Page, persona: { email?: string; password?: string }) {
  await page.context().clearCookies()
  await page.goto('/client/login')
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() }).catch(() => {})
  await page.goto('/client/login')
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
  await page.getByLabel(/email/i).fill(persona.email!)
  await page.getByLabel(/password/i).fill(persona.password!)
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/, { timeout: 20_000 })
}

async function loginAdmin(page: Page) {
  await page.context().clearCookies()
  await page.goto('/admin/login')
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() }).catch(() => {})
  await page.goto('/admin/login')
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
  await page.getByLabel(/email/i).fill(admin.email!)
  await page.getByLabel(/password/i).fill(admin.password!)
  await page.getByRole('button', { name: /sign in|log in/i }).click()
  await expect(page).toHaveURL(/\/admin\/?$/, { timeout: 20_000 })
}

async function expectNoHorizontalOverflow(page: Page) {
  const metrics = await page.evaluate(() => ({
    htmlOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    bodyOverflow: document.body.scrollWidth - document.body.clientWidth,
  }))
  expect(Math.max(metrics.htmlOverflow, metrics.bodyOverflow)).toBeLessThanOrEqual(2)
}

async function expectBasicAccessibility(page: Page) {
  const result = await page.evaluate(() => {
    const buttonsWithoutNames = Array.from(document.querySelectorAll('button')).filter(button => {
      const label = button.getAttribute('aria-label') || button.textContent || button.getAttribute('title') || ''
      return !label.trim()
    }).length
    const imagesWithoutAlt = Array.from(document.querySelectorAll('img')).filter(img => {
      if (img.getAttribute('aria-hidden') === 'true') return false
      return img.getAttribute('alt') === null
    }).length
    const invalidInputs = Array.from(document.querySelectorAll('input, textarea, select')).filter(input => {
      const id = input.getAttribute('id')
      const aria = input.getAttribute('aria-label') || input.getAttribute('aria-labelledby')
      return !aria && (!id || !document.querySelector(`label[for="${CSS.escape(id)}"]`))
    }).length
    const headings = Array.from(document.querySelectorAll('h1,h2,h3')).length
    return { buttonsWithoutNames, imagesWithoutAlt, invalidInputs, headings }
  })
  expect(result.buttonsWithoutNames).toBe(0)
  expect(result.imagesWithoutAlt).toBe(0)
  expect(result.headings).toBeGreaterThan(0)
}

async function verifyClientRoute(page: Page, route: string, panelClass: string, heading: RegExp) {
  const errors: string[] = []
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text())
  })
  await page.goto(route)
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
  await expect(page.locator('.wc-client-portal')).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('.wc-pageHost > .wc-panel')).toHaveCount(1)
  await expect(page.locator(`.wc-pageHost > .${panelClass}`)).toHaveCount(1)
  await expect(page.locator('.wc-pageHost .wc-heroExact')).toHaveCount(1)
  await expect(page.locator('.wc-pageHost')).toContainText(heading)
  await expect(page.locator('.wc-advisor')).toHaveCount(1)
  if (page.viewportSize()!.width > 1500) {
    await expect(page.locator('.wc-advisor')).toBeVisible()
  } else {
    await expect(page.locator('.wc-advisor')).toBeHidden()
  }
  await expect(page.locator('.wc-pageHost')).not.toContainText(/Purchased service/i)
  await expect(page.locator('.wc-pageHost')).not.toContainText(/Credit stage guidance/i)
  await expect(page.locator('.wc-pageHost .guided-client-journey')).toHaveCount(0)
  await expect(page.locator('[data-testid="client-revenue-service"]')).toHaveCount(0)
  await expectNoHorizontalOverflow(page)
  await expectBasicAccessibility(page)
  expect(errors.filter(text => !/favicon|Failed to load resource|TypeError: Failed to fetch/i.test(text))).toEqual([])
}

test.describe('Nexus 3 final authenticated certification', () => {
  test.setTimeout(180_000)
  test.skip(!enabled, 'Set E2E_ENABLE_AUTHENTICATED=true and synthetic account credentials.')

  for (const persona of [personaA, personaB, personaC]) {
    test.describe(persona.label, () => {
      test.skip(!persona.email || !persona.password, `${persona.label} credentials required`)

      test(`${persona.label}: production authenticated client routes use single Nexus 3 workspace`, async ({ page }) => {
        await loginClient(page, persona)
        for (const [route, panelClass, heading] of clientRoutes) {
          await verifyClientRoute(page, route, panelClass, heading)
        }
        await page.getByRole('button', { name: /Chat with Hermes/i }).click()
        await expect(page.getByRole('dialog', { name: /Ask Hermes/i })).toBeVisible()
        await expect(page.getByRole('dialog', { name: /Ask Hermes/i })).toContainText(/Current page context|Recommended actions/i)
        await page.getByRole('button', { name: /Close Hermes chat/i }).click()
        await page.locator('.wc-topSignOut').click()
        await expect(page).toHaveURL(/\/client\/login/, { timeout: 15_000 })
      })
    })
  }

  test('Persona B: ambiguity-safe language remains visible', async ({ page }) => {
    test.skip(!personaB.email || !personaB.password, 'Persona B credentials required')
    await loginClient(page, personaB)
    await page.goto('/client/account-details')
    await expect(page.locator('.wc-pageHost')).toContainText(/discrepanc|bureau|account/i)
    await expect(page.locator('.wc-pageHost')).not.toContainText(/automatically merged|guaranteed/i)
  })

  test('Persona C: ownership-discrepancy review path remains visible', async ({ page }) => {
    test.skip(!personaC.email || !personaC.password, 'Persona C credentials required')
    await loginClient(page, personaC)
    await page.goto('/client/credit-repair-journey')
    await expect(page.locator('.wc-pageHost')).toContainText(/evidence|GoClear|review/i)
    await expect(page.locator('.wc-pageHost')).not.toContainText(/guaranteed deletion|guaranteed score/i)
  })

  test('authenticated responsive client and admin surfaces do not overflow', async ({ browser }: { browser: Browser }) => {
    test.skip(!personaA.email || !personaA.password || !admin.email || !admin.password, 'Persona A and admin credentials required')
    for (const viewport of viewports) {
      const clientContext = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } })
      const clientPage = await clientContext.newPage()
      await loginClient(clientPage, personaA)
      await verifyClientRoute(clientPage, '/client/credit-profile', 'wc-panel-credit', /Credit Journey/i)
      await clientContext.close()

      const adminContext = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } })
      const adminPage = await adminContext.newPage()
      await loginAdmin(adminPage)
      await adminPage.goto('/admin#clients')
      await adminPage.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await expect(adminPage.locator('.os-root')).toBeVisible({ timeout: 15_000 })
      await expect(adminPage.getByRole('heading', { name: /^Clients$/i })).toBeVisible()
      await expect(adminPage.getByTestId('admin-client-list')).toBeVisible()
      await expectNoHorizontalOverflow(adminPage)
      await adminContext.close()
    }
  })

  test('Synthetic Admin: production operations workflow is accessible and guarded', async ({ page }) => {
    test.skip(!admin.email || !admin.password, 'Admin credentials required')
    await loginAdmin(page)
    await expect(page.locator('.os-root')).toBeVisible({ timeout: 15_000 })
    await page.goto('/admin#clients')
    await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
    await expect(page.getByRole('heading', { name: /^Clients$/i })).toBeVisible()
    await expect(page.getByPlaceholder(/Search clients/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Ask Hermes/i }).first()).toBeVisible()
    await page.getByTestId('admin-client-row').first().click()
    await expect(page.getByTestId('admin-client-detail-drawer')).toBeVisible()
    await expect(page.getByTestId('admin-client-detail-drawer')).toContainText(/Client detail/i)
    await expect(page.getByText(/Readiness Scores/i)).toBeVisible()
    await expect(page.getByText(/Documents/i)).toBeVisible()
    await expect(page.getByText(/Admin Notes/i)).toBeVisible()
    await page.getByPlaceholder(/Add internal notes/i).fill('Synthetic final certification note.')
    await page.getByRole('button', { name: /Save Note/i }).click()
    await expect(page.getByRole('button', { name: /Saved/i })).toBeVisible()
    await page.getByRole('button', { name: /^Approve$/i }).click()
    await expect(page.getByText(/Approval recorded/i)).toBeVisible()
    await page.goto('/admin#readiness-admin')
    await expect(page.getByTestId('readiness-admin')).toBeVisible()
    await page.getByTestId('tab-scoring').click()
    await expect(page.getByTestId('admin-scoring-view')).toBeVisible()
    await page.getByTestId('tab-notes').click()
    await expect(page.getByTestId('admin-notes-view')).toBeVisible()
    await page.getByTestId('tab-draft').click()
    await page.getByTestId('prepare-draft').click()
    await expect(page.getByTestId('draft-summary')).toBeVisible()
  })
})
