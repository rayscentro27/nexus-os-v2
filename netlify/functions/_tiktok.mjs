import crypto from 'node:crypto'

export const SCOPES = ['user.info.basic', 'video.upload', 'video.publish']
const API = 'https://open.tiktokapis.com'

export function json(statusCode, body, headers = {}) { return { statusCode, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', ...headers }, body: JSON.stringify(body) } }
export function env() {
  const runtimeEnv = String(process.env.TIKTOK_ENV || 'production').toLowerCase() === 'sandbox' ? 'sandbox' : 'production'
  const keyName = runtimeEnv === 'sandbox' ? 'TIKTOK_SANDBOX_CLIENT_KEY' : 'TIKTOK_CLIENT_KEY'
  const secretName = runtimeEnv === 'sandbox' ? 'TIKTOK_SANDBOX_CLIENT_SECRET' : 'TIKTOK_CLIENT_SECRET'
  const required = [keyName, secretName, 'TIKTOK_REDIRECT_URI', 'TIKTOK_TOKEN_ENCRYPTION_KEY']
  for (const key of required) if (!process.env[key]) throw new Error(`server_configuration_missing:${key}`)
  const clientKey = process.env[keyName]
  const clientSecret = process.env[secretName]
  const tokenEncryptionKey = process.env.TIKTOK_TOKEN_ENCRYPTION_KEY
  return { runtimeEnv, clientKey, clientSecret, redirectUri: process.env.TIKTOK_REDIRECT_URI, tokenEncryptionKey, TIKTOK_CLIENT_KEY: clientKey, TIKTOK_CLIENT_SECRET: clientSecret, TIKTOK_REDIRECT_URI: process.env.TIKTOK_REDIRECT_URI, TIKTOK_TOKEN_ENCRYPTION_KEY: tokenEncryptionKey }
}
export function random(size = 32) { return crypto.randomBytes(size).toString('base64url') }
export function pkce(verifier) { return crypto.createHash('sha256').update(verifier).digest('base64url') }
export function signState(value, secret) { return `${value}.${crypto.createHmac('sha256', secret).update(value).digest('base64url')}` }
export function validState(signed, secret) { const packed = String(signed || ''); const cut = packed.lastIndexOf('.'); if (cut <= 0) return false; const value = packed.slice(0, cut); const sig = packed.slice(cut + 1); const expected = crypto.createHmac('sha256', secret).update(value).digest('base64url'); const actual = Buffer.from(sig); const expectedBuffer = Buffer.from(expected); return actual.length === expectedBuffer.length && crypto.timingSafeEqual(actual, expectedBuffer) }
function key(raw) { const b = Buffer.from(raw, /^[0-9a-f]{64}$/i.test(raw) ? 'hex' : 'base64'); if (b.length !== 32) throw new Error('TIKTOK_TOKEN_ENCRYPTION_KEY_must_be_32_bytes_base64_or_64_hex'); return b }
export function seal(value, secret) { const iv = crypto.randomBytes(12); const cipher = crypto.createCipheriv('aes-256-gcm', key(secret), iv); const body = Buffer.concat([cipher.update(value, 'utf8'), cipher.final()]); return [iv, cipher.getAuthTag(), body].map(x => x.toString('base64url')).join('.') }
export function unseal(value, secret) { const [iv, tag, body] = String(value).split('.').map(x => Buffer.from(x, 'base64url')); const decipher = crypto.createDecipheriv('aes-256-gcm', key(secret), iv); decipher.setAuthTag(tag); return Buffer.concat([decipher.update(body), decipher.final()]).toString('utf8') }
export function cookie(name, value, maxAge = 600) { return `${name}=${encodeURIComponent(value)}; Max-Age=${maxAge}; Path=/; HttpOnly; Secure; SameSite=Lax` }
export function readCookie(event, name) { const raw = event.headers?.cookie || event.headers?.Cookie || ''; return raw.split(';').map(x => x.trim()).find(x => x.startsWith(`${name}=`))?.slice(name.length + 1) }
export async function userFromBearer(event, c) { const h = event.headers?.authorization || event.headers?.Authorization; if (!h?.startsWith('Bearer ')) throw new Error('authenticated_nexus_session_required'); const r = await fetch(`${c.url}/auth/v1/user`, { headers: { apikey: c.anon, authorization: h } }); const u = await r.json(); if (!r.ok || !u?.id) throw new Error('authenticated_nexus_session_required'); const membershipResponse = await fetch(`${c.url}/rest/v1/tenant_memberships?user_id=eq.${encodeURIComponent(u.id)}&select=tenant_id,role,client_id`, { headers: { apikey: c.anon, authorization: h } }); const memberships = await membershipResponse.json().catch(() => []); if (!membershipResponse.ok || !Array.isArray(memberships) || memberships.length === 0) throw new Error('tenant_membership_required'); const hintedTenant = u.user_metadata?.tenant_id || u.app_metadata?.tenant_id; const requestedTenant = event.headers?.['x-nexus-tenant-id'] || event.headers?.['X-Nexus-Tenant-Id']; const selectedTenant = requestedTenant || hintedTenant; const membership = selectedTenant ? memberships.find(x => String(x.tenant_id) === String(selectedTenant)) : memberships.length === 1 ? memberships[0] : null; if (!membership) throw new Error('tenant_binding_required'); return { id: u.id, tenant: String(membership.tenant_id), role: membership.role, clientId: membership.client_id || null, bearer: h }
}
export function config() { const c = env(); const url = (process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL || '').replace(/\/$/, ''); const anon = process.env.VITE_SUPABASE_ANON_KEY || process.env.SUPABASE_ANON_KEY; const privilegedKey = process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY || null; if (!url || !anon) throw new Error('server_configuration_missing:supabase_public'); return { ...c, url, anon, privilegedKey } }
export async function db(c, path, options = {}) { if (!c.privilegedKey) throw new Error('server_configuration_missing:supabase_privileged_key'); const r = await fetch(`${c.url}/rest/v1/${path}`, { ...options, headers: { apikey: c.privilegedKey, authorization: `Bearer ${c.privilegedKey}`, 'content-type': 'application/json', ...(options.headers || {}) } }); const b = await r.json().catch(() => null); if (!r.ok) throw new Error(b?.message || `supabase_${r.status}`); return b }
export async function dbAsUser(c, u, path, options = {}) { const r = await fetch(`${c.url}/rest/v1/${path}`, { ...options, headers: { apikey: c.anon, authorization: u.bearer, 'content-type': 'application/json', ...(options.headers || {}) } }); const b = await r.json().catch(() => null); if (!r.ok) throw new Error(b?.message || `supabase_${r.status}`); return b }
export async function tiktok(c, token, path, options = {}) { const r = await fetch(`${API}${path}`, { ...options, headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json', ...(options.headers || {}) } }); const b = await r.json().catch(() => null); return { ok: r.ok && b?.error?.code === 'ok', status: r.status, body: b }
}
