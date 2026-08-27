/* Governed Meta inbound callback.
 *
 * This function deliberately performs validation and normalization only. A
 * downstream persistence adapter must be added/configured before production
 * inbound delivery is claimed; no outbound reply or publishing is performed.
 */
import crypto from 'node:crypto'

const json = (statusCode, body) => ({ statusCode, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' }, body: JSON.stringify(body) })
const header = (event, name) => event.headers?.[name] || event.headers?.[name.toLowerCase()] || ''

export function verifyMetaSignature(rawBody, signature, appSecret) {
  if (!rawBody || !signature || !appSecret || !signature.startsWith('sha256=')) return false
  const expected = `sha256=${crypto.createHmac('sha256', appSecret).update(rawBody).digest('hex')}`
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(signature))
}

export function normalizeMetaPayload(payload) {
  const object = String(payload?.object || '')
  if (!['page', 'instagram'].includes(object)) return { accepted: false, reason: 'unsupported_meta_object' }
  const entries = Array.isArray(payload.entry) ? payload.entry : []
  const messages = []
  for (const entry of entries) {
    const sourceId = String(entry.id || '')
    for (const event of (entry.messaging || entry.changes || [])) {
      const sender = event.sender?.id || event.value?.from?.id
      const messageId = event.message?.mid || event.value?.message_id || event.id
      if (!sender || !messageId) continue
      messages.push({
        platform: object === 'instagram' ? 'instagram' : 'facebook_messenger',
        identity: `${object === 'instagram' ? 'ig' : 'fb'}:${String(sender)}`,
        thread_key: `${object}:${sourceId}:${String(sender)}`,
        message_id: String(messageId),
        received_at: new Date().toISOString(),
        content_present: Boolean(event.message?.text || event.value?.message),
      })
    }
  }
  return { accepted: true, object, messages, external_action_performed: false }
}

export async function handler(event) {
  const method = event.httpMethod || 'GET'
  if (method === 'GET') {
    const params = event.queryStringParameters || {}
    const configured = process.env.META_WEBHOOK_VERIFY_TOKEN
    if (!configured || params['hub.verify_token'] !== configured) return json(403, { error: 'verification_failed' })
    return { statusCode: 200, headers: { 'content-type': 'text/plain', 'cache-control': 'no-store' }, body: String(params['hub.challenge'] || '') }
  }
  if (method !== 'POST') return json(405, { error: 'method_not_allowed' })
  const rawBody = event.isBase64Encoded ? Buffer.from(event.body || '', 'base64').toString('utf8') : String(event.body || '')
  if (!verifyMetaSignature(rawBody, header(event, 'x-hub-signature-256'), process.env.META_APP_SECRET)) return json(403, { error: 'invalid_signature' })
  let payload
  try { payload = JSON.parse(rawBody) } catch { return json(400, { error: 'invalid_json' }) }
  const normalized = normalizeMetaPayload(payload)
  if (!normalized.accepted) return json(400, normalized)
  return json(200, { status: 'accepted_for_governed_ingestion', ...normalized, persistence: 'NOT_CONFIGURED', outbound_response: false })
}
