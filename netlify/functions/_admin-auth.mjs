const env = (key) => process.env[key] || ''

export async function requireAdmin(event) {
  const authorization = event.headers?.authorization || event.headers?.Authorization || ''
  if (!/^Bearer\s+\S+$/i.test(authorization)) return { ok: false, statusCode: 401, error: 'admin_authentication_required' }
  const url = (env('VITE_SUPABASE_URL') || env('SUPABASE_URL')).replace(/\/$/, '')
  const anon = env('VITE_SUPABASE_ANON_KEY') || env('SUPABASE_ANON_KEY')
  if (!url || !anon) return { ok: false, statusCode: 503, error: 'admin_authentication_unavailable' }
  const headers = { apikey: anon, authorization }
  const userResponse = await fetch(`${url}/auth/v1/user`, { headers }).catch(() => null)
  const user = userResponse ? await userResponse.json().catch(() => null) : null
  if (!userResponse?.ok || !user?.id) return { ok: false, statusCode: 401, error: 'authenticated_nexus_session_required' }
  const adminResponse = await fetch(`${url}/rest/v1/admin_users?id=eq.${encodeURIComponent(user.id)}&active=neq.false&select=role&limit=1`, { headers }).catch(() => null)
  const admins = adminResponse ? await adminResponse.json().catch(() => []) : []
  let role = Array.isArray(admins) && admins[0]?.role
  if (!role) {
    const membershipResponse = await fetch(`${url}/rest/v1/tenant_memberships?user_id=eq.${encodeURIComponent(user.id)}&role=in.(super_admin,admin,operator)&select=role&limit=1`, { headers }).catch(() => null)
    const memberships = membershipResponse ? await membershipResponse.json().catch(() => []) : []
    role = Array.isArray(memberships) && memberships[0]?.role
  }
  if (!role) return { ok: false, statusCode: 403, error: 'admin_access_required' }
  return { ok: true, userId: user.id, role: String(role) }
}
