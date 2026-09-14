import crypto from 'node:crypto'

export const SCOPES = ['user.info.basic', 'video.upload', 'video.publish']
const API = 'https://open.tiktokapis.com'

export function json(statusCode, body, headers = {}) { return { statusCode, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', ...headers }, body: JSON.stringify(body) } }
export function env() {
  const required = ['TIKTOK_CLIENT_KEY', 'TIKTOK_CLIENT_SECRET', 'TIKTOK_REDIRECT_URI', 'TIKTOK_TOKEN_ENCRYPTION_KEY']
  for (const key of required) if (!process.env[key]) throw new Error(`server_configuration_missing:${key}`)
  return Object.fromEntries(required.map(key => [key, process.env[key]]))
}
export function random(size = 32) { return crypto.randomBytes(size).toString('base64url') }
export function pkce(verifier) { return crypto.createHash('sha256').update(verifier).digest('base64url') }
export function signState(value, secret) { return `${value}.${crypto.createHmac('sha256', secret).update(value).digest('base64url')}` }
export function validState(signed, secret) { const [value, sig] = String(signed || '').split('.'); if (!value || !sig) return false; const expected = crypto.createHmac('sha256', secret).update(value).digest('base64url'); return crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected)) }
function key(raw) { const b = Buffer.from(raw, /^[0-9a-f]{64}$/i.test(raw) ? 'hex' : 'base64'); if (b.length !== 32) throw new Error('TIKTOK_TOKEN_ENCRYPTION_KEY_must_be_32_bytes_base64_or_64_hex'); return b }
export function seal(value, secret) { const iv = crypto.randomBytes(12); const cipher = crypto.createCipheriv('aes-256-gcm', key(secret), iv); const body = Buffer.concat([cipher.update(value, 'utf8'), cipher.final()]); return [iv, cipher.getAuthTag(), body].map(x => x.toString('base64url')).join('.') }
export function unseal(value, secret) { const [iv, tag, body] = String(value).split('.').map(x => Buffer.from(x, 'base64url')); const decipher = crypto.createDecipheriv('aes-256-gcm', key(secret), iv); decipher.setAuthTag(tag); return Buffer.concat([decipher.update(body), decipher.final()]).toString('utf8') }
export function cookie(name, value, maxAge = 600) { return `${name}=${encodeURIComponent(value)}; Max-Age=${maxAge}; Path=/; HttpOnly; Secure; SameSite=Lax` }
export function readCookie(event, name) { const raw = event.headers?.cookie || event.headers?.Cookie || ''; return raw.split(';').map(x => x.trim()).find(x => x.startsWith(`${name}=`))?.slice(name.length + 1) }
export async function userFromBearer(event, c) { const h = event.headers?.authorization || event.headers?.Authorization; if (!h?.startsWith('Bearer ')) throw new Error('authenticated_nexus_session_required'); const r = await fetch(`${c.url}/auth/v1/user`, { headers: { apikey: c.anon, authorization: h } }); const u = await r.json(); if (!r.ok || !u?.id) throw new Error('authenticated_nexus_session_required'); const tenant = u.user_metadata?.tenant_id || u.app_metadata?.tenant_id; if (!tenant) throw new Error('tenant_binding_required'); return { id: u.id, tenant: String(tenant), bearer: h }
}
export function config() { const c = env(); const url = (process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '').replace(/\/$/, ''); const anon = process.env.SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY; const service = process.env.SUPABASE_SERVICE_ROLE_KEY; if (!url || !anon || !service) throw new Error('server_configuration_missing:supabase'); return { ...c, url, anon, service } }
export async function db(c, path, options = {}) { const r = await fetch(`${c.url}/rest/v1/${path}`, { ...options, headers: { apikey: c.service, authorization: `Bearer ${c.service}`, 'content-type': 'application/json', ...(options.headers || {}) } }); const b = await r.json().catch(() => null); if (!r.ok) throw new Error(b?.message || `supabase_${r.status}`); return b }
export async function tiktok(c, token, path, options = {}) { const r = await fetch(`${API}${path}`, { ...options, headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json', ...(options.headers || {}) } }); const b = await r.json().catch(() => null); return { ok: r.ok && b?.error?.code === 'ok', status: r.status, body: b }
}
