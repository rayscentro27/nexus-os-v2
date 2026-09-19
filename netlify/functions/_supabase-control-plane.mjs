const env = (key) => process.env[key] || ''

export const supabaseConfig = () => ({
  url: (env('SUPABASE_URL') || env('VITE_SUPABASE_URL')).replace(/\/$/, ''),
  serviceKey: env('SUPABASE_SERVICE_ROLE_KEY'),
})

export async function supabaseRequest(path, { method = 'GET', body, headers = {} } = {}) {
  const { url, serviceKey } = supabaseConfig()
  if (!url || !serviceKey) throw new Error('supabase_control_plane_unavailable')
  const response = await fetch(`${url}/rest/v1/${path}`, {
    method,
    headers: { apikey: serviceKey, authorization: `Bearer ${serviceKey}`, 'content-type': 'application/json', ...(method !== 'GET' ? { Prefer: 'return=representation' } : {}), ...headers },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  const text = await response.text()
  let payload = null
  try { payload = text ? JSON.parse(text) : null } catch { payload = text }
  if (!response.ok) { const error = new Error(`supabase_request_failed:${response.status}`); error.status = response.status; error.payload = payload; throw error }
  return payload
}

export const canonicalApprovalId = (row) => row?.payload?.canonical_approval_id || row?.payload?.approval_id || null
export const companyCycleId = (row) => row?.payload?.company_cycle_id || row?.payload?.cycle_id || null

export async function readLiveControlPlane() {
  const [approvals, events] = await Promise.all([
    supabaseRequest('approvals?select=id,created_at,lane,item_type,item_id,status,title,summary,payload,approved_by,decided_at&order=created_at.desc&limit=200'),
    supabaseRequest('nexus_events?select=id,created_at,lane,source,action,status,title,summary,payload,correlation_id,approval_id&order=created_at.desc&limit=300'),
  ])
  return { approvals: Array.isArray(approvals) ? approvals : [], events: Array.isArray(events) ? events : [] }
}
