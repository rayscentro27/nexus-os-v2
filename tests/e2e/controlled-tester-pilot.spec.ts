import { expect, test, type Page } from 'playwright/test'

const requiredEnv = (name: string) => {
  const value = process.env[name]
  if (!value) throw new Error(`${name} is required for controlled tester pilot`)
  return value
}

requiredEnv('E2E_ENABLE_AUTHENTICATED')
const personas = {
  a: { email: requiredEnv('E2E_PERSONA_A_EMAIL'), password: requiredEnv('E2E_PERSONA_A_PASSWORD') },
  b: { email: requiredEnv('E2E_PERSONA_B_EMAIL'), password: requiredEnv('E2E_PERSONA_B_PASSWORD') },
  c: { email: requiredEnv('E2E_PERSONA_C_EMAIL'), password: requiredEnv('E2E_PERSONA_C_PASSWORD') },
}
const admin = { email: requiredEnv('E2E_ADMIN_EMAIL'), password: requiredEnv('E2E_ADMIN_PASSWORD') }
const supabaseUrl = requiredEnv('VITE_SUPABASE_URL')
const supabaseKey = requiredEnv('VITE_SUPABASE_ANON_KEY')

async function loginClient(page: Page, credentials: { email: string; password: string }, path: string) {
  await page.goto('/client/login')
  await page.waitForLoadState('domcontentloaded')
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
  await page.waitForLoadState('domcontentloaded')
  await page.getByLabel(/email/i).fill(admin.email)
  await page.getByLabel(/password/i).fill(admin.password)
  await page.getByRole('button', { name: /sign in|log in|submit/i }).click()
  await expect(page).toHaveURL(/\/admin\//, { timeout: 15_000 })
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
  await page.waitForTimeout(2000)
}

async function assertNoOverflow(page: Page) {
  const metrics = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, viewport: window.innerWidth }))
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.viewport + 2)
}

async function uploadFromGuidedStage(page: Page, fileName: string, category: string) {
  const stage = page.locator('.wc-guidedStage').first()
  await stage.getByRole('button', { name: /^(Upload|Replace Upload)$/ }).first().click()
  const dialog = page.getByRole('dialog').last()
  await expect(dialog).toBeVisible()
  const fileInput = dialog.locator('input[type="file"]').first()
  await expect(fileInput).toHaveCount(1)
  await fileInput.setInputFiles({ name: fileName, mimeType: 'text/plain', buffer: Buffer.from('Synthetic controlled pilot document. No client data.') })
  const categorySelect = dialog.locator('select').first()
  if (await categorySelect.count()) await categorySelect.selectOption(category)
  await dialog.getByRole('button', { name: 'Upload', exact: true }).click()
  await expect(dialog.getByText(/Uploaded to|Upload failed/i).last()).toBeVisible({ timeout: 30_000 })
  await expect(dialog.getByText(/Uploaded to/i).last()).toBeVisible()
}

async function readAdminToken(page: Page) {
  return page.evaluate(() => {
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i)
      if (!key?.endsWith('-auth-token')) continue
      try {
        const parsed = JSON.parse(localStorage.getItem(key) || '{}')
        const token = parsed?.currentSession?.access_token || parsed?.access_token
        if (token) return token
      } catch {}
    }
    return null
  })
}

async function createSession(page: Page, persona: 'a' | 'b' | 'c') {
  await page.getByRole('button', { name: 'Start Session', exact: true }).nth(['a', 'b', 'c'].indexOf(persona)).click()
  const modal = page.getByRole('heading', { name: new RegExp(`Start Tester Session — Persona ${persona.toUpperCase()}`) }).locator('..')
  const fields = modal.getByRole('textbox')
  await fields.nth(0).fill(`Synthetic Pilot ${persona.toUpperCase()}`)
  await fields.nth(1).fill(JSON.stringify({ browser: 'Chromium', device: 'desktop-1920x1080', fixture: 'controlled-pilot-v1', workflows: 12 }))
  await modal.getByRole('button', { name: 'Start Session', exact: true }).click()
  await expect(modal).toBeHidden({ timeout: 10_000 })
}

async function submitFeedback(page: Page, persona: 'a' | 'b' | 'c', severity: 'medium' | 'low') {
  await page.getByRole('button', { name: 'Report Issue', exact: true }).nth(['a', 'b', 'c'].indexOf(persona)).click()
  const modal = page.getByRole('heading', { name: new RegExp(`Report Issue — Persona ${persona.toUpperCase()}`) }).locator('../..')
  const inputs = modal.locator('input')
  const textareas = modal.locator('textarea')
  await inputs.nth(0).fill('/client/controlled-pilot')
  await inputs.nth(1).fill('structured pilot checklist')
  await inputs.nth(2).fill(`Controlled pilot observation Persona ${persona.toUpperCase()}`)
  await textareas.nth(0).fill('The controlled pilot checklist should remain actionable and scoped.')
  await textareas.nth(1).fill('The current guided task and next action are visible.')
  await textareas.nth(2).fill('Observed guided task completion without unsafe execution.')
  await modal.locator('select').nth(0).selectOption(severity)
  await modal.locator('select').nth(1).selectOption('always')
  await inputs.nth(3).fill('synthetic-ui-observation')
  await inputs.nth(4).fill('Chromium / controlled pilot viewport')
  await modal.getByRole('button', { name: 'Submit Issue', exact: true }).click()
  await expect(modal).toBeHidden({ timeout: 10_000 })
}

test.describe.configure({ mode: 'serial' })

test.describe('controlled three-person tester pilot', () => {
  test('Persona A completes the guided checklist through the real client UI', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await loginClient(page, personas.a, '/client/dashboard')
    const dashboard = page.getByTestId('guided-dashboard')
    await expect(dashboard.getByText(/Funding Readiness/i).first()).toBeVisible()
    await expect(dashboard.getByText(/Current journey stage/i)).toBeVisible()
    await expect(dashboard.getByText(/Next best action/i)).toBeVisible()
    await dashboard.getByRole('button', { name: /Continue where you left off/i }).click()
    await expect(page).toHaveURL(/\/client\/(credit-profile|business-setup|business-bankability|funding-readiness|request-review)/)

    await page.goto('/client/credit-profile')
    await expect(page.getByText(/Clyde Strategy Cards/i)).toBeVisible()
    await expect(page.getByText(/Approved educational strategy|Evidence that may help/i).first()).toBeVisible()
    await uploadFromGuidedStage(page, 'controlled-pilot-a-credit-evidence-final.txt', 'credit_evidence')
    await page.getByRole('button', { name: /Close upload panel/i }).click()

    await page.getByRole('button', { name: /Chat with Clyde/i }).click()
    await expect(page.getByRole('dialog', { name: /Ask Clyde/i })).toBeVisible()
    await expect(page.getByRole('dialog').getByText(/Current page context|Recommended actions/i).first()).toBeVisible()
    await page.getByRole('button', { name: /Close Clyde chat/i }).click()

    await page.goto('/client/documents')
    await expect(page.getByText(/Documents Vault/i).first()).toBeVisible()
    await expect(page.getByText(/Credit Evidence|Business Formation|Banking|Revenue & Financials|Funding Applications/i).first()).toBeVisible()
    await expect(page.getByText('controlled-pilot-a-credit-evidence-final.txt').first()).toBeVisible({ timeout: 20_000 })

    await page.goto('/client/funding-readiness')
    const funding = page.getByTestId('guided-funding-readiness')
    await expect(funding.getByText(/Credit contribution/i)).toBeVisible()
    await expect(funding.getByText(/Business Foundation contribution/i)).toBeVisible()
    await expect(funding.getByText(/Business Bankability contribution/i)).toBeVisible()

    await page.goto('/client/request-review')
    const review = page.getByTestId('guided-request-review')
    await expect(review.getByText(/eligible|not eligible/i).first()).toBeVisible()
    await expect(review.getByText(/not a guarantee of approval or funding/i)).toBeVisible()
    await expect(page.getByText(/No external message or document submission was triggered|specialist visibility/i).first()).toBeVisible()
  })

  test('Persona B keeps the genuine exception as the primary blocker', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
    await loginClient(page, personas.b, '/client/dashboard')
    await expect(page.getByText(/Primary blocker/i).first()).toBeVisible()
    await expect(page.getByText(/specialist review|Genuine exception/i).first()).toBeVisible()
    await page.goto('/client/credit-profile')
    await expect(page.locator('.wc-strategyCard').first()).toBeVisible()
    const body = await page.locator('body').innerText()
    expect(body).toMatch(/uncertain|specialist review|Nexus cannot guarantee/i)
    expect(body).not.toMatch(/automatic deletion|guaranteed removal|guaranteed score/i)
    await page.getByRole('button', { name: /Chat with Clyde/i }).click()
    await expect(page.getByRole('dialog', { name: /Ask Clyde/i })).toBeVisible()
    await expect(page.getByRole('dialog').getByText(/uncertain|specialist|what.*know/i).first()).toBeVisible()
  })

  test('Persona C completes the purchased-debt documentation path', async ({ page }) => {
    await loginClient(page, personas.c, '/client/funding-readiness')
    await expect(page.getByText(/Purchased-debt documentation/i).first()).toBeVisible()
    await expect(page.getByRole('button', { name: /upload/i }).first()).toBeVisible()
    await page.goto('/client/credit-profile')
    await expect(page.getByText(/Purchased Debt Documentation Review/i)).toBeVisible()
    await expect(page.getByText(/Evidence that may help|safe draft|Prepare Draft/i).first()).toBeVisible()
    await expect(page.getByText(/Funding Readiness/i).first()).toBeVisible()
  })

  test('Synthetic admin creates, reviews, routes, and closes the three pilot sessions', async ({ page }) => {
    await loginAdmin(page)
    await page.goto('/admin#tester-readiness')
    await expect(page.getByText(/Tester Readiness/i).first()).toBeVisible({ timeout: 15_000 })

    for (const persona of ['a', 'b', 'c'] as const) await createSession(page, persona)
    for (const [persona, severity] of [['a', 'medium'], ['b', 'low'], ['c', 'medium']] as const) await submitFeedback(page, persona, severity)

    for (const persona of ['a', 'b', 'c'] as const) {
      const card = page.locator(`[data-persona-card="${persona}"]`)
      await card.getByRole('button', { name: 'Details', exact: true }).click()
      const complete = card.getByRole('button', { name: 'Complete Session', exact: true }).first()
      await expect(complete).toBeVisible({ timeout: 10_000 })
      await complete.click()
      await page.waitForTimeout(500)
    }

    const linked = page.getByRole('button', { name: /Open linked Ray Review draft/i }).first()
    await expect(linked).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText(/Tester backlog/i).first()).toBeVisible()
    await linked.click()
    await expect(page.getByRole('heading', { name: /^Ray Review$/i })).toBeVisible()

    const token = await readAdminToken(page)
    expect(token).toBeTruthy()
    const persisted = await page.evaluate(async ({ url, key, token }) => {
      const headers = { apikey: key, Authorization: `Bearer ${token}` }
      const sessions = await fetch(`${url}/rest/v1/tester_sessions?select=id,tester_name,status&tester_name=in.(Synthetic%20Pilot%20A,Synthetic%20Pilot%20B,Synthetic%20Pilot%20C)`, { headers }).then(r => r.json())
      const feedback = await fetch(`${url}/rest/v1/tester_feedback?select=id,issue_title,severity,ray_review_item_id&issue_title=like.Controlled%20pilot%20observation%25`, { headers }).then(r => r.json())
      const reviews = await fetch(`${url}/rest/v1/task_requests?select=id,payload&task_type=eq.ray_review_item&requested_by=eq.tester_feedback&limit=200`, { headers }).then(r => r.json())
      return { sessions, feedback, reviews }
    }, { url: supabaseUrl, key: supabaseKey, token })
    expect(persisted.sessions.length).toBeGreaterThanOrEqual(3)
    for (const persona of ['A', 'B', 'C']) {
      expect(persisted.sessions.some((row: { tester_name: string; status: string }) => row.tester_name === `Synthetic Pilot ${persona}` && row.status === 'completed')).toBeTruthy()
    }
    expect(persisted.feedback.length).toBeGreaterThanOrEqual(3)
    expect(persisted.feedback.some((row: { severity: string; ray_review_item_id: string | null }) => ['medium', 'low'].includes(row.severity) && !row.ray_review_item_id)).toBeTruthy()
    const linkedFeedback = persisted.feedback.find((row: { ray_review_item_id: string | null }) => row.ray_review_item_id)
    if (linkedFeedback) {
      const matching = persisted.reviews.filter((row: { payload?: { feedback_record_id?: string } }) => row.payload?.feedback_record_id === linkedFeedback.id)
      expect(matching).toHaveLength(1)
    }
  })

  test('Client sessions cannot access admin tester controls', async ({ page }) => {
    await loginClient(page, personas.a, '/client/dashboard')
    await page.goto('/admin#tester-readiness')
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => {})
    await expect(page.getByText(/admin access required|Admin login/i).first()).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/Persona A/i)).toHaveCount(0)
  })

  for (const [name, width, height] of [['desktop', 1920, 1080], ['laptop', 1366, 768], ['tablet', 768, 1024], ['mobile', 390, 844]] as const) {
    test(`${name} pilot viewport keeps actions and navigation accessible`, async ({ page }) => {
      await page.setViewportSize({ width, height })
      await loginClient(page, personas.a, '/client/dashboard')
      await assertNoOverflow(page)
      await expect(page.getByTestId('guided-dashboard').getByRole('button', { name: /Continue where you left off/i })).toBeVisible()
      await expect(page.getByRole('button', { name: /Documents/i }).first()).toBeVisible()
      if (width > 1500) await expect(page.getByRole('button', { name: /Chat with Clyde/i })).toBeVisible()
      else await expect(page.getByText(/Clyde guidance/i).first()).toBeVisible()
    })
  }
})
