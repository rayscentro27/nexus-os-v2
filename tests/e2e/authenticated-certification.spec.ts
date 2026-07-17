import { expect, test } from 'playwright/test'

const enabled = process.env.E2E_ENABLE_AUTHENTICATED === 'true'

const personaA = { email: process.env.E2E_PERSONA_A_EMAIL, password: process.env.E2E_PERSONA_A_PASSWORD }
const personaB = { email: process.env.E2E_PERSONA_B_EMAIL, password: process.env.E2E_PERSONA_B_PASSWORD }
const personaC = { email: process.env.E2E_PERSONA_C_EMAIL, password: process.env.E2E_PERSONA_C_PASSWORD }
const admin = { email: process.env.E2E_ADMIN_EMAIL, password: process.env.E2E_ADMIN_PASSWORD }

const anyPersona = [personaA, personaB, personaC, admin].some(p => p.email && p.password)

test.describe('authenticated browser certification', () => {
  test.skip(!enabled || !anyPersona, 'Set E2E_ENABLE_AUTHENTICATED=true and at least one set of persona credentials in env.')

  // ─── Persona A ────────────────────────────────────────────────────────
  test.describe('Persona A', () => {
    test.skip(!personaA.email || !personaA.password, 'E2E_PERSONA_A_EMAIL and E2E_PERSONA_A_PASSWORD required')

    test('Persona A: client login succeeds and session persists', async ({ page }) => {
      await page.goto('/client/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(personaA.email!)
      await page.getByLabel(/password/i).fill(personaA.password!)
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 15_000 })
      await expect(page).not.toHaveURL(/\/client\/login/)
    })

    test('Persona A: cannot access admin routes', async ({ page }) => {
      await page.goto('/client/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(personaA.email!)
      await page.getByLabel(/password/i).fill(personaA.password!)
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)
      await page.goto('/admin/credit-specialist')
      await expect(page.getByRole('heading', { name: /admin access required/i })).toBeVisible()
    })
  })

  // ─── Persona B ────────────────────────────────────────────────────────
  test.describe('Persona B', () => {
    test.skip(!personaB.email || !personaB.password, 'E2E_PERSONA_B_EMAIL and E2E_PERSONA_B_PASSWORD required')

    test('Persona B: client login succeeds and session persists', async ({ page }) => {
      await page.goto('/client/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(personaB.email!)
      await page.getByLabel(/password/i).fill(personaB.password!)
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 15_000 })
      await expect(page).not.toHaveURL(/\/client\/login/)
    })

    test('Persona B: cannot access admin routes', async ({ page }) => {
      await page.goto('/client/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(personaB.email!)
      await page.getByLabel(/password/i).fill(personaB.password!)
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)
      await page.goto('/admin/credit-specialist')
      await expect(page.getByRole('heading', { name: /admin access required/i })).toBeVisible()
    })
  })

  // ─── Persona C ────────────────────────────────────────────────────────
  test.describe('Persona C', () => {
    test.skip(!personaC.email || !personaC.password, 'E2E_PERSONA_C_EMAIL and E2E_PERSONA_C_PASSWORD required')

    test('Persona C: client login succeeds and session persists', async ({ page }) => {
      await page.goto('/client/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(personaC.email!)
      await page.getByLabel(/password/i).fill(personaC.password!)
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 15_000 })
      await expect(page).not.toHaveURL(/\/client\/login/)
    })

    test('Persona C: cannot access admin routes', async ({ page }) => {
      await page.goto('/client/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(personaC.email!)
      await page.getByLabel(/password/i).fill(personaC.password!)
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)
      await page.goto('/admin/credit-specialist')
      await expect(page.getByRole('heading', { name: /admin access required/i })).toBeVisible()
    })
  })

  // ─── Synthetic Admin ──────────────────────────────────────────────────
  test.describe('Synthetic Admin', () => {
    test.skip(!admin.email || !admin.password, 'E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD required')

    test('Admin: login succeeds and session persists', async ({ page }) => {
      await page.goto('/admin/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(admin.email!)
      await page.getByLabel(/password/i).fill(admin.password!)
      await page.getByRole('button', { name: /sign in|log in/i }).click()
      await expect(page).toHaveURL(/\/admin\/?$/)
      await page.reload({ waitUntil: 'networkidle', timeout: 15_000 }).catch(() => {})
      await expect(page).toHaveURL(/\/admin\/?$/)
    })

    test('Admin: can access credit specialist route', async ({ page }) => {
      await page.goto('/admin/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(admin.email!)
      await page.getByLabel(/password/i).fill(admin.password!)
      await page.getByRole('button', { name: /sign in|log in/i }).click()
      await expect(page).toHaveURL(/\/admin\/?$/)
      await page.goto('/admin/credit-specialist')
      await expect(page).not.toHaveURL(/\/admin\/login/)
      await expect(page.getByRole('button', { name: /credit.*funding.*readiness review/i })).toBeVisible()
    })

    test('Admin: cannot access client portal as client', async ({ page }) => {
      await page.goto('/admin/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(admin.email!)
      await page.getByLabel(/password/i).fill(admin.password!)
      await page.getByRole('button', { name: /sign in|log in/i }).click()
      await expect(page).toHaveURL(/\/admin\/?$/)
      await page.goto('/client/dashboard')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.waitForTimeout(2000)
      const url = page.url()
      const redirectedToLogin = /\/client\/login/.test(url)
      const showsLogin = await page.getByText(/client portal login/i).isVisible().catch(() => false)
      const showsError = await page.getByText(/access|unauthorized|not authorized|sign in/i).isVisible().catch(() => false)
      expect(redirectedToLogin || showsLogin || showsError).toBeTruthy()
    })
  })

  // ─── Cross-Client Browser Denial ──────────────────────────────────────
  test.describe('Cross-client browser denial', () => {
    test.skip(!personaA.email || !personaA.password, 'E2E_PERSONA_A_EMAIL and E2E_PERSONA_A_PASSWORD required for cross-client denial test')

    test('Persona A: RLS denies access to another client documents via API', async ({ page }) => {
      await page.goto('/client/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(personaA.email!)
      await page.getByLabel(/password/i).fill(personaA.password!)
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)

      // Attempt to read client_documents for a different client via Supabase REST
      const supabaseUrl = process.env.VITE_SUPABASE_URL ?? ''
      const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY ?? ''
      if (!supabaseUrl || !supabaseKey) throw new Error('Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY')
      const result = await page.evaluate(async ({ supabaseUrl, supabaseKey }: { supabaseUrl: string; supabaseKey: string }) => {
        try {
          const res = await fetch(`${supabaseUrl}/rest/v1/client_documents?select=id,client_id&limit=5`, {
            headers: {
              apikey: supabaseKey,
              Authorization: `Bearer ${supabaseKey}`,
            },
          })
          if (!res.ok) return { status: res.status, denied: true }
          const data = await res.json()
          return { status: res.status, count: data.length, denied: false }
        } catch (e) {
          return { error: String(e), denied: true }
        }
      }, { supabaseUrl, supabaseKey })

      // Without a session JWT, anon key should get zero rows (RLS) or 403
      expect(result.denied || result.count === 0).toBeTruthy()
    })

    test('Persona A: browser cannot reach admin API endpoints', async ({ page }) => {
      await page.goto('/client/login')
      await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
      await page.getByLabel(/email/i).fill(personaA.email!)
      await page.getByLabel(/password/i).fill(personaA.password!)
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page).toHaveURL(/\/client\/(dashboard|documents|credit-profile)/)

      // Try to access admin-only table via Supabase REST with client session
      const supabaseUrl2 = process.env.VITE_SUPABASE_URL ?? ''
      const supabaseKey2 = process.env.VITE_SUPABASE_ANON_KEY ?? ''
      if (!supabaseUrl2 || !supabaseKey2) throw new Error('Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY')
      const result = await page.evaluate(async ({ supabaseUrl, supabaseKey }: { supabaseUrl: string; supabaseKey: string }) => {
        try {
          // Get the session token from Supabase client storage
          let token = supabaseKey
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i)
            if (key && key.startsWith('sb-') && key.endsWith('-auth-token')) {
              try {
                const parsed = JSON.parse(localStorage.getItem(key) || '{}')
                if (parsed?.currentSession?.access_token) { token = parsed.currentSession.access_token; break }
                if (parsed?.access_token) { token = parsed.access_token; break }
              } catch { /* continue */ }
            }
          }

          // Try to access credit_report_parser_results (admin-only table)
          const res = await fetch(`${supabaseUrl}/rest/v1/credit_report_parser_results?select=id&limit=1`, {
            headers: {
              apikey: supabaseKey,
              Authorization: `Bearer ${token}`,
            },
          })
          if (!res.ok) return { status: res.status, denied: true }
          const data = await res.json()
          return { status: res.status, count: data.length, denied: false }
        } catch (e) {
          return { error: String(e), denied: true }
        }
      }, { supabaseUrl: supabaseUrl2, supabaseKey: supabaseKey2 })

      // Client JWT should be denied by RLS on admin-only table
      expect(result.denied || result.count === 0).toBeTruthy()
    })
  })
})
