import { expect, test, type Page } from 'playwright/test'

const requiredEnv = (name: string) => {
  const value = process.env[name]
  if (!value) throw new Error(`${name} is required for guided portal certification`)
  return value
}

requiredEnv('E2E_ENABLE_AUTHENTICATED')
const personaA = { email: requiredEnv('E2E_PERSONA_A_EMAIL'), password: requiredEnv('E2E_PERSONA_A_PASSWORD') }
const personaB = { email: requiredEnv('E2E_PERSONA_B_EMAIL'), password: requiredEnv('E2E_PERSONA_B_PASSWORD') }
const personaC = { email: requiredEnv('E2E_PERSONA_C_EMAIL'), password: requiredEnv('E2E_PERSONA_C_PASSWORD') }
const admin = { email: requiredEnv('E2E_ADMIN_EMAIL'), password: requiredEnv('E2E_ADMIN_PASSWORD') }
const supabaseUrl = requiredEnv('VITE_SUPABASE_URL')
const supabaseKey = requiredEnv('VITE_SUPABASE_ANON_KEY')

async function loginClient(page: Page, credentials: { email: string; password: string }, path: string) {
  await page.goto('/client/login')
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
  await page.getByLabel(/email/i).fill(credentials.email)
  await page.getByLabel(/password/i).fill(credentials.password)
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/, { timeout: 15_000 })
  await page.goto(path)
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
  await expect(page.locator('.wc-client-portal')).toBeVisible({ timeout: 15_000 })
}

async function loginAdmin(page: Page) {
  await page.goto('/admin/login')
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
  await page.getByLabel(/email/i).fill(admin.email)
  await page.getByLabel(/password/i).fill(admin.password)
  await page.getByRole('button', { name: /sign in|log in/i }).click()
  await expect(page).toHaveURL(/\/admin\/?$/)
}

test.describe('guided client portal certification', () => {
  test.describe('Persona A — guided funding readiness', () => {
    test('dashboard shows status, current stage, and working next action', async ({ page }) => {
      await loginClient(page, personaA, '/client/dashboard')
      const dashboard = page.getByTestId('guided-dashboard')
      await expect(dashboard).toBeVisible()
      await expect(dashboard.getByText(/Funding Readiness/i).first()).toBeVisible()
      await expect(dashboard.getByText(/Current journey stage/i)).toBeVisible()
      await expect(dashboard.getByText(/Next best action/i)).toBeVisible()
      await expect(dashboard.getByRole('button', { name: /Continue where you left off/i })).toBeVisible()
      const primaryNav = page.locator('.wc-sideNav')
      for (const label of ['Home', 'Credit', 'Business', 'Funding Readiness', 'Documents', 'Resources', 'Request Review']) {
        await expect(primaryNav.locator('.wc-navLabel').filter({ hasText: label })).toBeVisible()
      }
      await expect(primaryNav.getByRole('button')).toHaveCount(7)
      await expect(primaryNav.locator('.wc-navLabel').filter({ hasText: /Credit Utilization|Business Bankability|Affiliates/i })).toHaveCount(0)
      await dashboard.getByRole('button', { name: /Continue where you left off/i }).click()
      await expect(page).toHaveURL(/\/client\/(credit-profile|business-setup|business-bankability|funding-readiness|request-review)/)
    })

    test('Credit stage opens with contextual inline upload coverage', async ({ page }) => {
      await loginClient(page, personaA, '/client/credit-profile')
      const stage = page.getByTestId('guided-stage-credit_profile')
      await expect(stage).toBeVisible()
      await expect(stage.getByText(/Credit stage|Credit Profile/i).first()).toBeVisible()
      await expect(page.getByText(/Credit Profile and Credit Utilization are one guided stage/i)).toBeVisible()
      await expect(stage.getByRole('button', { name: /upload/i }).first()).toBeVisible()
      await expect(page.getByText(/Bureau coverage|Utilization summary|Approved Strategy Cards/i).first()).toBeVisible()
    })

    test('Documents Vault categories render and safe draft remains accessible', async ({ page }) => {
      await loginClient(page, personaA, '/client/documents')
      const vault = page.getByTestId('guided-documents-vault')
      await expect(vault).toBeVisible()
      for (const category of ['Credit Reports', 'Credit Evidence', 'Identity and Authorization', 'Business Formation', 'Banking', 'Revenue and Financials', 'Funding Applications', 'Other']) {
        await expect(vault.getByText(category, { exact: true })).toBeVisible()
      }
      await page.goto('/client/credit-profile')
      await page.getByRole('button', { name: /Open safe draft review/i }).click()
      await expect(page).toHaveURL(/\/client\/dispute-review/)
    })

    test('Request Review eligibility is explicit and no-guarantee language is present', async ({ page }) => {
      await loginClient(page, personaA, '/client/request-review')
      const review = page.getByTestId('guided-request-review')
      await expect(review).toBeVisible()
      await expect(review.getByText(/eligible|not eligible/i).first()).toBeVisible()
      await expect(review.getByText(/Review deliverable|readiness snapshot/i).first()).toBeVisible()
      await expect(review.getByText(/not a guarantee of approval or funding/i)).toBeVisible()
    })
  })

  test.describe('Persona B — genuine exception', () => {
    test('exception is the primary blocker and specialist review is visible', async ({ page }) => {
      await loginClient(page, personaB, '/client/dashboard')
      await expect(page.getByText(/Genuine exception requires specialist review|specialist review/i).first()).toBeVisible()
      await expect(page.getByText(/Primary blocker/i).first()).toBeVisible()
    })

    test('unsafe strategy language is absent and readiness is not falsely complete', async ({ page }) => {
      await loginClient(page, personaB, '/client/credit-profile')
      const body = await page.locator('body').innerText()
      expect(body).not.toMatch(/automatic deletion|guaranteed removal|guaranteed score/i)
      expect(body).toMatch(/Nexus cannot guarantee|not guaranteed/i)
      await expect(page.getByText(/action needed|almost ready|not eligible/i).first()).toBeVisible()
    })
  })

  test.describe('Persona C — purchased-debt evidence', () => {
    test('purchased-debt documentation requirement and contextual upload appear', async ({ page }) => {
      await loginClient(page, personaC, '/client/funding-readiness')
      const funding = page.getByTestId('guided-funding-readiness')
      await expect(funding.getByText(/Purchased-debt documentation/i).first()).toBeVisible()
      await expect(funding.getByRole('button', { name: /upload/i }).first()).toBeVisible()
      await expect(funding.getByText(/Missing \/ next action|Upload purchased-debt documentation/i).first()).toBeVisible()
    })

    test('strategy remains visible and journey progress reflects persisted state', async ({ page }) => {
      await loginClient(page, personaC, '/client/credit-profile')
      await expect(page.getByText(/Clyde Strategy Cards/i)).toBeVisible()
      await expect(page.getByText(/Funding Readiness/i).first()).toBeVisible()
      await expect(page.getByText(/Done/i).first()).toBeVisible()
      await expect(page.getByText(/Remaining/i).first()).toBeVisible()
    })
  })

  test.describe('Synthetic admin linkage and isolation', () => {
    test('client and tester records remain isolated', async ({ page }) => {
      await loginClient(page, personaA, '/client/dashboard')
      const result = await page.evaluate(async ({ url, key }) => {
        let token = key
        for (let i = 0; i < localStorage.length; i += 1) {
          const storageKey = localStorage.key(i)
          if (!storageKey?.endsWith('-auth-token')) continue
          try {
            const parsed = JSON.parse(localStorage.getItem(storageKey) || '{}')
            token = parsed?.currentSession?.access_token || parsed?.access_token || token
          } catch {}
        }
        const response = await fetch(`${url}/rest/v1/tester_feedback?select=id&limit=1`, { headers: { apikey: key, Authorization: `Bearer ${token}` } })
        if (!response.ok) return { denied: true, count: 0 }
        const rows = await response.json()
        return { denied: false, count: rows.length }
      }, { url: supabaseUrl, key: supabaseKey })
      expect(result.denied || result.count === 0).toBeTruthy()
    })

    test('client journey status, blocker, and tester feedback link to Ray Review draft', async ({ page }) => {
      await loginAdmin(page)
      await page.goto('/admin#tester-readiness')
      await expect(page.getByRole('heading', { name: /Tester Readiness/i })).toBeVisible()
      await expect(page.getByText(/Persona A/i).first()).toBeVisible()
      await page.getByRole('button', { name: /^Details$/ }).first().click()
      const linkedDraft = page.getByRole('button', { name: /Open linked Ray Review draft/i }).first()
      let linkedVisible = false
      try {
        await expect(linkedDraft).toBeVisible({ timeout: 15_000 })
        linkedVisible = true
      } catch {}
      if (!linkedVisible) {
        await page.getByRole('button', { name: /Create Ray Review draft/i }).first().click()
        await expect(page.getByText(/Ray Review draft linked/i)).toBeVisible({ timeout: 10_000 })
      }
      await expect(page.getByText(/Primary blocker|Needs Ray Review|Ray Review linked/i).first()).toBeVisible()
      await expect(page.getByRole('button', { name: /Open linked Ray Review draft/i }).first()).toBeVisible()
      await page.getByRole('button', { name: /Open linked Ray Review draft/i }).first().click()
      await expect(page.getByRole('heading', { name: /^Ray Review$/i })).toBeVisible()
      await expect(page.getByText(/Live Supabase/i).first()).toBeVisible()
      await expect(page.getByText(/Guided portal Ray Review routing certification|BLOCKER.*Persona A/i).first()).toBeVisible()
    })
  })

  test.describe('Responsive guided portal', () => {
    for (const [name, width, height] of [['desktop', 1920, 1080], ['laptop', 1366, 768], ['mobile', 390, 844]] as const) {
      test(`${name} viewport has no horizontal overflow and keeps primary action accessible`, async ({ page }) => {
        await page.setViewportSize({ width, height })
        await loginClient(page, personaA, '/client/dashboard')
        const metrics = await page.evaluate(() => ({ width: document.documentElement.scrollWidth, viewport: window.innerWidth }))
        expect(metrics.width).toBeLessThanOrEqual(metrics.viewport + 2)
        await expect(page.getByTestId('guided-dashboard').getByRole('button', { name: /Continue where you left off/i })).toBeVisible()
        await expect(page.getByRole('button', { name: /Documents/i }).first()).toBeVisible()
      })
    }
  })
})
