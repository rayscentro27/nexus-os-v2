const env = (key) => process.env[key] || ''
const ACCEPTED_ADMIN_ROLES = new Set(['super_admin', 'admin', 'operator'])

const projectRef = (url) => {
  try { return new URL(url).hostname.split('.')[0] || 'unknown' } catch { return 'unknown' }
}

const failure = (statusCode, diagnostic, ref, lookup = undefined) => {
  // Keep diagnostics bounded and safe: never include the bearer, user id, or raw provider error.
  console.warn('[requireAdmin]', JSON.stringify({ diagnostic, project_ref: ref, ...(lookup ? { lookup } : {}) }))
  return { ok: false, statusCode, error: diagnostic, projectRef: ref }
}

export async function requireAdmin(event) {
  const authorization = event.headers?.authorization || event.headers?.Authorization || ''
  if (!/^Bearer\s+\S+$/i.test(authorization)) return { ok: false, statusCode: 401, error: 'AUTH_FAILED' }
  const url = (env('VITE_SUPABASE_URL') || env('SUPABASE_URL')).replace(/\/$/, '')
  const anon = env('VITE_SUPABASE_ANON_KEY') || env('SUPABASE_ANON_KEY')
  if (!url || !anon) return { ok: false, statusCode: 503, error: 'AUTH_SERVICE_UNAVAILABLE' }
  const ref = projectRef(url)
  const userResponse = await fetch(`${url}/auth/v1/user`, {
    headers: { apikey: anon, authorization },
  }).catch(() => null)
  if (!userResponse) return failure(503, 'AUTH_SERVICE_UNAVAILABLE', ref)
  const user = await userResponse.json().catch(() => null)
  if (!userResponse.ok || !user?.id) return failure(401, 'AUTH_FAILED', ref)
  console.info('[requireAdmin]', JSON.stringify({ diagnostic: 'AUTH_USER_FOUND', project_ref: ref }))

  // Verify the user's JWT above, then read role state with the server-only key so RLS
  // cannot turn a legitimate role-query failure into a false "not an admin" result.
  const serviceKey = env('SUPABASE_SECRET_KEY') || env('SUPABASE_SERVICE_ROLE_KEY')
  if (!serviceKey) return failure(503, 'ROLE_LOOKUP_UNAVAILABLE', ref)
  const headers = { apikey: serviceKey, authorization: `Bearer ${serviceKey}` }
  const adminUrl = `${url}/rest/v1/admin_users?id=eq.${encodeURIComponent(user.id)}&select=role,active&limit=1`
  const adminResponse = await fetch(adminUrl, { headers }).catch(() => null)
  if (!adminResponse) return failure(503, 'ADMIN_QUERY_ERROR', ref, 'admin_users')
  const admins = await adminResponse.json().catch(() => null)
  if (!adminResponse.ok || !Array.isArray(admins)) return failure(503, 'ADMIN_QUERY_ERROR', ref, 'admin_users')

  const adminRecord = admins[0]
  if (!adminRecord) {
    console.info('[requireAdmin]', JSON.stringify({ diagnostic: 'ADMIN_RECORD_NOT_FOUND', project_ref: ref }))
  }
  if (adminRecord?.active === false) {
    console.info('[requireAdmin]', JSON.stringify({ diagnostic: 'ADMIN_RECORD_INACTIVE', project_ref: ref }))
  }
  const activeRole = adminRecord?.active !== false ? String(adminRecord?.role || '') : ''
  if (activeRole && ACCEPTED_ADMIN_ROLES.has(activeRole)) {
    return { ok: true, userId: user.id, role: activeRole, projectRef: ref }
  }

  const membershipUrl = `${url}/rest/v1/tenant_memberships?user_id=eq.${encodeURIComponent(user.id)}&role=in.(super_admin,admin,operator)&select=role&limit=1`
  const membershipResponse = await fetch(membershipUrl, { headers }).catch(() => null)
  if (!membershipResponse) return failure(503, 'ADMIN_QUERY_ERROR', ref, 'tenant_memberships')
  const memberships = await membershipResponse.json().catch(() => null)
  if (!membershipResponse.ok || !Array.isArray(memberships)) return failure(503, 'ADMIN_QUERY_ERROR', ref, 'tenant_memberships')

  const membershipRole = String(memberships[0]?.role || '')
  if (membershipRole && ACCEPTED_ADMIN_ROLES.has(membershipRole)) {
    return { ok: true, userId: user.id, role: membershipRole, projectRef: ref }
  }

  const diagnostic = adminRecord?.active === false
    ? 'ADMIN_RECORD_INACTIVE'
    : adminRecord && adminRecord.role
      ? 'ROLE_NOT_ACCEPTED'
      : 'TENANT_MEMBERSHIP_NOT_FOUND'
  return failure(403, diagnostic, ref)
}
