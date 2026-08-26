const ORIGIN = 'https://goclearonline.cc'
const MAX_AUDIO_BYTES = 10 * 1024 * 1024
const ALLOWED_TYPES = new Set(['audio/webm', 'audio/webm;codecs=opus', 'audio/wav', 'audio/x-wav', 'audio/aiff', 'audio/mpeg', 'application/octet-stream'])

const response = (statusCode, body, origin = ORIGIN) => ({ statusCode, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true', vary: 'Origin' }, body: JSON.stringify(body) })

export async function handler(event) {
  const requestOrigin = event.headers?.origin || event.headers?.Origin || ORIGIN
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: { 'access-control-allow-origin': requestOrigin === ORIGIN ? ORIGIN : 'null', 'access-control-allow-credentials': 'true', 'access-control-allow-methods': 'POST, OPTIONS', 'access-control-allow-headers': 'authorization, content-type, x-nexus-voice-session, x-nexus-voice-preview-sequence', 'access-control-max-age': '300', vary: 'Origin' }, body: '' }
  if (requestOrigin !== ORIGIN) return response(403, { error: 'origin-not-allowed' }, 'null')
  if (event.httpMethod !== 'POST') return response(405, { error: 'method_not_allowed' })
  const auth = event.headers?.authorization || event.headers?.Authorization || ''
  if (!/^Bearer\s+\S+$/i.test(auth)) return response(401, { error: 'authentication-required' })
  const contentType = String(event.headers?.['content-type'] || event.headers?.['Content-Type'] || '').split(';')[0].toLowerCase()
  if (!ALLOWED_TYPES.has(contentType)) return response(415, { error: 'audio-type-not-allowed' })
  const encoded = event.body || ''
  const bytes = event.isBase64Encoded ? Math.floor(encoded.length * 3 / 4) : Buffer.byteLength(encoded)
  if (!bytes || bytes > MAX_AUDIO_BYTES) return response(413, { error: 'audio-size-bounded' })
  if (!process.env.VOICE_ACCESS_ORIGIN || !process.env.CF_ACCESS_CLIENT_ID || !process.env.CF_ACCESS_CLIENT_SECRET) return response(503, { error: 'voice_relay_not_configured' })
  const userCheck = await fetch(`${process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL}/auth/v1/user`, { headers: { authorization: auth, apikey: process.env.VITE_SUPABASE_ANON_KEY || '' } }).catch(() => null)
  if (!userCheck?.ok) return response(401, { error: 'nexus_authentication_failed' })
  const mode = event.queryStringParameters?.mode === 'preview' ? 'preview' : 'transcribe'
  const upstream = await fetch(`${process.env.VOICE_ACCESS_ORIGIN}/v1/voice/${mode}`, { method: 'POST', headers: { 'content-type': contentType, 'cf-access-client-id': process.env.CF_ACCESS_CLIENT_ID, 'cf-access-client-secret': process.env.CF_ACCESS_CLIENT_SECRET, 'x-nexus-voice-session': String(event.headers?.['x-nexus-voice-session'] || '').slice(0, 120) }, body: Buffer.from(encoded, event.isBase64Encoded ? 'base64' : 'utf8') }).catch(() => null)
  if (!upstream) return response(504, { error: 'voice_upstream_timeout' })
  const body = await upstream.text()
  let payload = {}; try { payload = JSON.parse(body) } catch { payload = { error: 'voice_upstream_invalid_response' } }
  return response(upstream.status, payload)
}
