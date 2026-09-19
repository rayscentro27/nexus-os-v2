import { requireAdmin } from './_admin-auth.mjs'

const ORIGIN = 'https://goclearonline.cc'
const NOVA_TARGET = process.env.NOVA_TARGET_URL || process.env.NEXUS_NOVA_ENDPOINT || 'https://nova.goclearonline.cc/v1/nova/chat'
const MAX_MESSAGE_CHARS = 4000
const MAX_HISTORY_MESSAGES = 12
const MAX_HISTORY_CHARS = 14000
const SENSITIVE = /(?:\b\d{3}-\d{2}-\d{4}\b|\b(?:ssn|social security|bank account|routing number|date of birth|credit report)\b|\b[^\s@]+@[^\s@]+\.[^\s@]+\b)/i

const response = (statusCode, body, origin = ORIGIN) => ({
  statusCode,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store', 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', vary: 'Origin' },
  body: JSON.stringify(body),
})

function allowedOrigin(event) {
  const requestOrigin = event.headers?.origin || event.headers?.Origin || ORIGIN
  if (requestOrigin === ORIGIN) return ORIGIN
  const host = String(event.headers?.host || event.headers?.Host || '').toLowerCase()
  const canary = `https://${host}`
  return /^[a-z0-9][a-z0-9-]*--nexusv20\.netlify\.app$/.test(host) && requestOrigin === canary ? canary : null
}

function boundedPayload(event) {
  let payload
  try { payload = JSON.parse(event.body || '{}') } catch { throw Object.assign(new Error('invalid_json'), { statusCode: 400 }) }
  const message = payload?.message
  if (typeof message !== 'string' || !message.trim() || message.length > MAX_MESSAGE_CHARS) throw Object.assign(new Error('message-bounded'), { statusCode: 400 })
  if (SENSITIVE.test(message)) throw Object.assign(new Error('client-sensitive-input-not-available-in-nova-browser'), { statusCode: 400 })
  const conversationId = payload?.conversation_id
  if (typeof conversationId !== 'string' || !/^[A-Za-z0-9_-]{8,120}$/.test(conversationId)) throw Object.assign(new Error('conversation-id-bounded'), { statusCode: 400 })
  const history = payload?.recent_history || []
  if (!Array.isArray(history) || history.length > MAX_HISTORY_MESSAGES) throw Object.assign(new Error('history-bounded'), { statusCode: 400 })
  let historyChars = 0
  const recentHistory = history.map((item) => {
    if (!item || !['user', 'assistant'].includes(item.role) || typeof item.content !== 'string') throw Object.assign(new Error('history-contract-invalid'), { statusCode: 400 })
    const content = item.content.trim().slice(0, 2400)
    historyChars += content.length
    return { role: item.role, content }
  })
  if (historyChars > MAX_HISTORY_CHARS) throw Object.assign(new Error('history-size-bounded'), { statusCode: 413 })
  return { message: message.trim(), conversationId, recentHistory }
}

function accessHeaders() {
  // NOVA_* names allow a separately scoped Access service token. The legacy
  // names are accepted for the existing governed server-side deployment where
  // the same Access application protects the canonical Nova origin.
  const clientId = process.env.NOVA_CF_ACCESS_CLIENT_ID || process.env.CF_ACCESS_CLIENT_ID
  const clientSecret = process.env.NOVA_CF_ACCESS_CLIENT_SECRET || process.env.CF_ACCESS_CLIENT_SECRET
  if (!clientId || !clientSecret) return null
  return { 'cf-access-client-id': clientId, 'cf-access-client-secret': clientSecret }
}

export async function handler(event) {
  const origin = allowedOrigin(event)
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: { 'access-control-allow-origin': origin || 'null', 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'POST, OPTIONS', 'access-control-allow-headers': 'authorization, content-type, x-nexus-nova-session', 'access-control-max-age': '300', vary: 'Origin' }, body: '' }
  if (!origin) return response(403, { error: 'origin-not-allowed' }, 'null')
  if (event.httpMethod !== 'POST') return response(405, { error: 'method_not_allowed' }, origin)
  const auth = await requireAdmin(event)
  if (!auth.ok) return response(auth.statusCode, { error: auth.error }, origin)
  const access = accessHeaders()
  if (!access) return response(503, { error: 'nova_server_bridge_not_configured' }, origin)
  let payload
  try { payload = boundedPayload(event) } catch (error) { return response(error.statusCode || 400, { error: error.message || 'invalid_request' }, origin) }
  const headers = { ...access, 'content-type': 'application/json', origin: ORIGIN, referer: `${ORIGIN}/admin` }
  const upstream = await fetch(NOVA_TARGET, { method: 'POST', redirect: 'manual', headers: { ...headers, 'x-nexus-nova-session': payload.conversationId }, body: JSON.stringify({ message: payload.message, conversation_id: payload.conversationId, channel: 'admin_browser', recent_history: payload.recentHistory }) }).catch(() => null)
  if (!upstream) return response(504, { error: 'nova_upstream_unreachable' }, origin)
  if (upstream.status >= 300 && upstream.status < 400) return response(502, { error: 'nova_access_redirect_not_allowed' }, origin)
  const raw = await upstream.text()
  let body = {}; try { body = JSON.parse(raw) } catch { body = { error: 'nova_upstream_invalid_response' } }
  if (!upstream.ok) return response(502, { error: body.error || 'nova_upstream_failed', upstream_status: upstream.status }, origin)
  return response(200, { ...body, transport: 'netlify_server_to_server', admin_role: auth.role, canonical_profile: body.profile || 'nova_nexus', secrets_exposed: false }, origin)
}
