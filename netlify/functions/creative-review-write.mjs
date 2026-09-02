const ALLOWED_ACTIONS = new Set(['APPROVE', 'REQUEST_REVISION', 'REJECT', 'ARCHIVE', 'COMMENT'])
const json = (statusCode, body) => ({ statusCode, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }, body: JSON.stringify(body) })

function config() {
  const url = process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  const anonKey = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY
  if (!url || !serviceKey || !anonKey) throw new Error('Supabase server configuration is incomplete.')
  return { url: url.replace(/\/$/, ''), serviceKey, anonKey }
}

async function supabaseRequest(c, path, options = {}) {
  const response = await fetch(`${c.url}/rest/v1/${path}`, { ...options, headers: { apikey: c.serviceKey, Authorization: `Bearer ${c.serviceKey}`, 'Content-Type': 'application/json', ...(options.headers || {}) } })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new Error(body?.message || body?.error_description || `Supabase request failed (${response.status}).`)
  return body
}

async function authenticate(event, c) {
  const authorization = event.headers?.authorization || event.headers?.Authorization
  if (!authorization?.startsWith('Bearer ')) throw new Error('Authenticated operator session required.')
  const token = authorization.slice(7)
  const userResponse = await fetch(`${c.url}/auth/v1/user`, { headers: { apikey: c.anonKey, Authorization: `Bearer ${token}` } })
  const user = await userResponse.json().catch(() => null)
  if (!userResponse.ok || !user?.id) throw new Error('Authenticated operator session required.')
  const admins = await supabaseRequest(c, `admin_users?id=eq.${encodeURIComponent(user.id)}&active=eq.true&select=id,email,role&limit=1`)
  if (!admins?.length) throw new Error('Operator authorization required.')
  return { id: user.id, email: user.email, role: admins[0].role }
}

function validate(input) {
  if (!input || typeof input !== 'object') throw new Error('JSON review input required.')
  if (!input.asset_id || typeof input.asset_id !== 'string' || input.asset_id.length > 180) throw new Error('Valid asset_id required.')
  const version = Number(input.version)
  if (!Number.isInteger(version) || version < 1) throw new Error('Positive integer version required.')
  if (!ALLOWED_ACTIONS.has(input.action)) throw new Error('Review action is not permitted.')
  if (input.feedback != null && (typeof input.feedback !== 'string' || input.feedback.length > 2000)) throw new Error('Feedback must be text up to 2,000 characters.')
  if (!input.request_id || typeof input.request_id !== 'string' || input.request_id.length > 300) throw new Error('Idempotency request_id required.')
  return { asset_id: input.asset_id, version, action: input.action, feedback: input.feedback?.trim() || '', request_id: input.request_id }
}

function reviewStatus(action) { return ({ APPROVE: 'APPROVED_FOR_NEXT_INTERNAL_STAGE', REQUEST_REVISION: 'REVISION_REQUESTED', REJECT: 'REJECTED_RETAINED', ARCHIVE: 'ARCHIVED', COMMENT: 'COMMENTED' })[action] }

export async function handler(event) {
  try {
    const c = config()
    const reviewer = await authenticate(event, c)
    if (event.httpMethod === 'GET') {
      const reviews = await supabaseRequest(c, 'approvals?item_type=eq.creative_asset_review&select=*&order=created_at.desc&limit=100')
      return json(200, { reviews: reviews || [] })
    }
    if (event.httpMethod !== 'POST') return json(405, { error: 'Method not allowed.' })
    const input = validate(JSON.parse(event.body || '{}'))
    const existing = await supabaseRequest(c, `approvals?item_type=eq.creative_asset_review&payload->>request_id=eq.${encodeURIComponent(input.request_id)}&select=*&limit=1`)
    if (existing?.length) return json(200, { idempotent: true, review: existing[0], reviewer: reviewer.email })
    const status = reviewStatus(input.action)
    const row = { lane: 'creative', item_type: 'creative_asset_review', status: input.action === 'REQUEST_REVISION' ? 'revise' : input.action === 'APPROVE' ? 'approved' : input.action === 'REJECT' ? 'rejected' : 'pending', title: `${status}: ${input.asset_id} v${input.version}`, summary: input.feedback || 'Internal Creative review decision.', approved_by: reviewer.email || reviewer.id, decided_at: new Date().toISOString(), payload: { asset_id: input.asset_id, version: input.version, action: input.action, request_id: input.request_id, feedback: input.feedback, publication_triggered: false, reviewer_id: reviewer.id } }
    const inserted = await supabaseRequest(c, 'approvals', { method: 'POST', headers: { Prefer: 'return=representation' }, body: JSON.stringify(row) })
    let revisionWorkOrder = null
    if (input.action === 'REQUEST_REVISION') {
      const tasks = await supabaseRequest(c, `task_requests?task_type=eq.creative_review_revision&payload->>request_id=eq.${encodeURIComponent(input.request_id)}&select=id&limit=1`)
      if (!tasks?.length) {
        const created = await supabaseRequest(c, 'task_requests', { method: 'POST', headers: { Prefer: 'return=representation' }, body: JSON.stringify({ task_type: 'creative_review_revision', requested_by: reviewer.email || reviewer.id, sensitivity: 'internal_summary', allowed_data_scope: ['creative_review', 'creative_asset'], forbidden_data: ['customer_private', 'secrets', 'payments', 'publishing'], assigned_worker_type: 'creative', hermes_visibility: 'summary', status: 'requested', payload: { request_id: input.request_id, asset_id: input.asset_id, version: input.version, feedback: input.feedback, parent_asset_id: input.asset_id, publication_triggered: false } }) })
        revisionWorkOrder = created?.[0] || created
      } else revisionWorkOrder = tasks[0]
    }
    return json(201, { idempotent: false, review: inserted?.[0] || inserted, revision_work_order: revisionWorkOrder, reviewer: reviewer.email })
  } catch (error) { return json(error.message.includes('required') || error.message.includes('Valid') || error.message.includes('permitted') || error.message.includes('Feedback') || error.message.includes('integer') || error.message.includes('Idempotency') ? 400 : 500, { error: error.message }) }
}
