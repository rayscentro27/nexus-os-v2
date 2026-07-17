import { test, expect } from 'playwright/test'
import { existsSync, readFileSync } from 'fs'
import { resolve } from 'path'
import { createClient } from '@supabase/supabase-js'

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'

function loadLocalE2EEnv() {
  for (const envPath of [resolve(process.cwd(), '.env'), resolve(process.cwd(), '.env.e2e.local')]) {
    if (!existsSync(envPath)) continue
    for (const line of readFileSync(envPath, 'utf-8').split('\n')) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith('#') || !trimmed.includes('=')) continue
      const [key, ...valueParts] = trimmed.split('=')
      if (!process.env[key]) process.env[key] = valueParts.join('=').replace(/^['"]|['"]$/g, '')
    }
  }
}

loadLocalE2EEnv()

const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL || ''
const anonKey = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY || ''
const adminEmail = process.env.E2E_ADMIN_EMAIL || process.env.VITE_E2E_ADMIN_EMAIL || process.env.ADMIN_EMAIL || ''
const adminPassword = process.env.E2E_ADMIN_PASSWORD || process.env.VITE_E2E_ADMIN_PASSWORD || process.env.ADMIN_PASSWORD || ''

test.describe('Wave 1 invited tester journey', () => {
  test('tester redeems one-time invitation and receives live portal baseline', async ({ page }) => {
    test.skip(!supabaseUrl || !anonKey || !adminEmail || !adminPassword, 'Supabase and synthetic admin credentials required')

    const adminClient = createClient(supabaseUrl, anonKey, { auth: { persistSession: false } })
    const adminLogin = await adminClient.auth.signInWithPassword({ email: adminEmail, password: adminPassword })
    expect(adminLogin.error).toBeNull()

    const testerEmail = `wave1.browser.${Date.now()}@goclear.test`
    const createRes = await fetch(`${supabaseUrl}/functions/v1/create-tester-invitation`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${adminLogin.data.session!.access_token}`,
        apikey: anonKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        testerName: 'Wave One Browser Tester',
        testerEmail,
        testingLevel: 'friends_family_free',
        assignedTenantId: 'goclear',
        expiresInDays: 14,
        personalMessage: 'Synthetic Wave 1 browser certification invitation.',
      }),
    })
    const created = await createRes.json()
    expect(createRes.status, created.error || created.detail).toBe(200)
    expect(created.raw_token).toMatch(/^[a-f0-9]{64}$/)

    const password = `Wave1!${Date.now()}x`
    await page.goto(`${BASE_URL}/invite/accept?token=${created.raw_token}`)
    await expect(page.getByTestId('password-input')).toBeVisible({ timeout: 20_000 })
    await page.getByTestId('password-input').fill(password)
    await page.getByTestId('confirm-password-input').fill(password)
    await page.getByTestId('consent-checkbox').check()
    await page.getByTestId('accept-invitation-btn').click()
    await expect(page.getByTestId('start-journey-btn')).toBeVisible({ timeout: 20_000 })
    await page.getByTestId('start-journey-btn').click()
    await page.waitForURL('**/client/login?accepted=1', { timeout: 20_000 })
    await page.getByPlaceholder('Enter your email address').fill(testerEmail)
    await page.getByPlaceholder('Enter your password').fill(password)
    await page.getByRole('button', { name: /^Sign In$/ }).click()
    await page.waitForURL('**/client/dashboard', { timeout: 20_000 })
    await expect(page.getByText(/Funding Readiness/i).first()).toBeVisible({ timeout: 20_000 })

    const reuseRes = await fetch(`${supabaseUrl}/functions/v1/accept-tester-invitation`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${anonKey}`, apikey: anonKey, 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: created.raw_token, password, consentAccepted: true }),
    })
    const reused = await reuseRes.json()
    expect(reuseRes.status).toBe(409)
    expect(reused.error).toBe('invitation_already_accepted')

    const testerClient = createClient(supabaseUrl, anonKey, { auth: { persistSession: false } })
    const testerLogin = await testerClient.auth.signInWithPassword({ email: testerEmail, password })
    expect(testerLogin.error).toBeNull()
    const jwt = testerLogin.data.session!.access_token
    const authedClient = createClient(supabaseUrl, anonKey, {
      auth: { persistSession: false },
      global: { headers: { Authorization: `Bearer ${jwt}` } },
    })

    const memberships = await authedClient.from('tenant_memberships').select('tenant_id,client_id,role')
    expect(memberships.error).toBeNull()
    expect(memberships.data).toHaveLength(1)
    const clientId = memberships.data![0].client_id
    expect(memberships.data![0]).toMatchObject({ tenant_id: 'goclear', role: 'client' })

    const [profileRes, taskRes, scoreRes, crossProfileRes] = await Promise.all([
      authedClient.from('client_profiles').select('client_id,status,client_visible').eq('client_id', clientId),
      authedClient.from('client_tasks').select('id,status').eq('client_id', clientId).eq('client_visible', true),
      authedClient.from('readiness_scores').select('category,status').eq('client_id', clientId).eq('client_visible', true),
      authedClient.from('client_profiles').select('client_id').neq('client_id', clientId).limit(5),
    ])
    expect(profileRes.error).toBeNull()
    expect(taskRes.error).toBeNull()
    expect(scoreRes.error).toBeNull()
    expect(crossProfileRes.error).toBeNull()
    expect(profileRes.data).toHaveLength(1)
    expect(taskRes.data).toHaveLength(3)
    expect(scoreRes.data?.map(row => row.category).sort()).toEqual(['business_profile', 'credit_profile', 'credit_repair', 'funding_readiness'])
    expect(crossProfileRes.data).toHaveLength(0)

    const invitationCheck = await adminClient
      .from('tester_invitations')
      .select('invitation_status,assigned_client_id,assigned_tenant_id')
      .eq('id', created.invitation.id)
      .maybeSingle()
    expect(invitationCheck.error).toBeNull()
    expect(invitationCheck.data).toMatchObject({
      invitation_status: 'accepted',
      assigned_client_id: clientId,
      assigned_tenant_id: 'goclear',
    })
  })
})
