import snapshot from '../../src/data/adminCompanyState.json'

const json = (statusCode, body) => ({ statusCode, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' }, body: JSON.stringify(body) })
const env = (key) => process.env[key] || ''

export async function handler(event) {
  try {
    const authorization = event.headers?.authorization || event.headers?.Authorization
    if (!authorization?.startsWith('Bearer ')) return json(401, { error: 'admin_authentication_required' })
    const url = (env('VITE_SUPABASE_URL') || env('SUPABASE_URL')).replace(/\/$/, '')
    const anon = env('VITE_SUPABASE_ANON_KEY') || env('SUPABASE_ANON_KEY')
    if (!url || !anon) return json(503, { error: 'admin_read_model_unavailable' })
    const userResponse = await fetch(`${url}/auth/v1/user`, { headers: { apikey: anon, authorization } })
    const user = await userResponse.json().catch(() => null)
    if (!userResponse.ok || !user?.id) return json(401, { error: 'authenticated_nexus_session_required' })
    const headers = { apikey: anon, authorization, 'content-type': 'application/json' }
    const adminResponse = await fetch(`${url}/rest/v1/admin_users?id=eq.${encodeURIComponent(user.id)}&active=neq.false&select=role&limit=1`, { headers })
    const admins = await adminResponse.json().catch(() => [])
    let role = Array.isArray(admins) && admins[0]?.role
    if (!role) {
      const membershipResponse = await fetch(`${url}/rest/v1/tenant_memberships?user_id=eq.${encodeURIComponent(user.id)}&role=in.(super_admin,admin,operator)&select=role&limit=1`, { headers })
      const memberships = await membershipResponse.json().catch(() => [])
      role = Array.isArray(memberships) && memberships[0]?.role
    }
    if (!role) return json(403, { error: 'admin_access_required' })
    return json(200, {
      ...snapshot,
      generated_at: new Date().toISOString(),
      read_model: 'authenticated_admin_projection',
      authorization: { allowed: true, role: String(role) },
      sensitive_fields_excluded: true,
    })
  } catch {
    return json(500, { error: 'admin_read_model_failed' })
  }
}
