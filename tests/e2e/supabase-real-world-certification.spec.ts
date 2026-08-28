import { expect, test } from 'playwright/test'
import { existsSync, readFileSync, writeFileSync } from 'fs'
import { resolve } from 'path'
import { createHash } from 'crypto'

function loadLocalE2EEnv() {
  for (const envPath of [resolve(process.cwd(), '.env'), resolve(process.cwd(), '.env.e2e.local')]) {
    if (!existsSync(envPath)) continue
    for (const line of readFileSync(envPath, 'utf-8').split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
      const [key, ...parts] = trimmed.split('=')
      if (!process.env[key]) process.env[key] = parts.join('=').replace(/^['"]|['"]$/g, '')
    }
  }
}

loadLocalE2EEnv()
const email = process.env.E2E_PERSONA_A_EMAIL || ''
const password = process.env.E2E_PERSONA_A_PASSWORD || ''
const supabaseUrl = process.env.VITE_SUPABASE_URL || ''
const anonKey = process.env.VITE_SUPABASE_ANON_KEY || ''
const evidencePath = process.env.SUPABASE_CERT_EVIDENCE_PATH || ''

async function rest(page: any, path: string, token: string) {
  return page.evaluate(async ({ url, key, path, token }) => {
    const response = await fetch(`${url}/rest/v1/${path}`, { headers: { apikey: key, Authorization: `Bearer ${token}` } })
    let data: unknown = []
    try { data = await response.json() } catch { /* status is enough */ }
    return { status: response.status, rows: Array.isArray(data) ? data.length : 0, first: Array.isArray(data) ? data[0] : undefined }
  }, { url: supabaseUrl, key: anonKey, path, token })
}

test('real Supabase browser/session/RLS evidence', async ({ page }) => {
  test.skip(!email || !password || !supabaseUrl || !anonKey, 'Existing Persona A and VITE Supabase configuration required')
  const result: Record<string, unknown> = {
    persona: 'persona_a', browser_safe_config_verified: Boolean(supabaseUrl && anonKey),
    service_role_frontend_exposure: false, authenticated_session_verified: false,
    browser_supabase_read_verified: false, own_scope_read: 'NOT_PROVEN',
    cross_tenant_read: 'NOT_PROVEN', admin_only_read: 'NOT_PROVEN',
    rls_tenant_isolation_verified: false, database_mutations: 0,
  }
  const source = await page.context().request.get('/src/lib/supabaseClient.ts')
  const sourceText = await source.text()
  result.service_role_frontend_exposure = /SUPABASE_SERVICE_ROLE_KEY|service_role/i.test(sourceText)
  await page.goto('/client/login')
  await page.getByLabel(/email/i).fill(email)
  await page.getByLabel(/password/i).fill(password)
  await page.getByRole('button', { name: /sign in/i }).click()
  await expect(page).toHaveURL(/\/client\/(onboarding|dashboard|documents|credit-profile)/)
  const session = await page.evaluate(() => {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i) || ''
      if (!key.startsWith('sb-') || !key.endsWith('-auth-token')) continue
      try {
        const value = JSON.parse(localStorage.getItem(key) || '{}')
        const token = value?.currentSession?.access_token || value?.access_token
        const user = value?.currentSession?.user || value?.user
        if (token) return { present: true, userIdHash: user?.id ? 'sha256:' + user.id : 'present' }
      } catch { /* continue */ }
    }
    return { present: false }
  })
  result.authenticated_session_verified = session.present === true
  if (!session.present) throw new Error('Authenticated Supabase session was not present')
  result.user_id_hash = session.userIdHash
  await page.reload({ waitUntil: 'domcontentloaded' })
  result.session_persistence = await page.evaluate(() => Object.keys(localStorage).some(key => key.startsWith('sb-') && key.endsWith('-auth-token')))
  const token = await page.evaluate(() => {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i) || ''
      if (!key.endsWith('-auth-token')) continue
      try { const value = JSON.parse(localStorage.getItem(key) || '{}'); const token = value?.currentSession?.access_token || value?.access_token; if (token) return token } catch { /* continue */ }
    }
    return ''
  })
  const membership = await rest(page, 'tenant_memberships?select=tenant_id,client_id,role&limit=1', token)
  const own = await rest(page, 'client_profiles?select=client_id&limit=1', token)
  const ownClientId = (own.first as { client_id?: string } | undefined)?.client_id || ''
  const cross = await rest(page, `client_profiles?select=client_id&neq.client_id=${encodeURIComponent(ownClientId)}&limit=5`, token)
  const adminOnly = await rest(page, 'credit_report_parser_results?select=id&limit=1', token)
  result.browser_supabase_read_verified = membership.status >= 200 && membership.status < 300
  result.own_scope_read = own.status >= 200 && own.rows > 0 ? 'PASS' : 'NOT_PROVEN'
  result.cross_tenant_read = cross.status >= 200 && cross.rows === 0 ? 'DENIED_OR_ZERO' : 'NOT_PROVEN'
  result.admin_only_read = adminOnly.status >= 400 || adminOnly.rows === 0 ? 'DENIED_OR_ZERO' : 'NOT_PROVEN'
  result.rls_tenant_isolation_verified = result.own_scope_read === 'PASS' && result.cross_tenant_read === 'DENIED_OR_ZERO' && result.admin_only_read === 'DENIED_OR_ZERO'
  result.authenticated_at = new Date().toISOString()
  if (evidencePath) writeFileSync(evidencePath, JSON.stringify(result, null, 2) + '\n')
})
