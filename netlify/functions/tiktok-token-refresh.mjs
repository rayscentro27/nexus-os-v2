import { config, db, json, seal, unseal, userFromBearer } from './_tiktok.mjs'

export async function handler(event) {
  try {
    if (event.httpMethod !== 'POST') return json(405, { error: 'method_not_allowed' })
    const c = config()
    const u = await userFromBearer(event, c)
    const rows = await db(c, `nexus_tiktok_connections?user_id=eq.${encodeURIComponent(u.id)}&tenant_id=eq.${encodeURIComponent(u.tenant)}&status=eq.CONNECTED&select=*&limit=1`)
    const connection = rows?.[0]
    if (!connection?.encrypted_refresh_token) return json(404, { error: 'refresh_token_not_available' })
    const refresh = unseal(connection.encrypted_refresh_token, c.TIKTOK_TOKEN_ENCRYPTION_KEY)
    const response = await fetch('https://open.tiktokapis.com/v2/oauth/token/', { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ client_key: c.TIKTOK_CLIENT_KEY, client_secret: c.TIKTOK_CLIENT_SECRET, grant_type: 'refresh_token', refresh_token: refresh }) })
    const token = await response.json().catch(() => ({}))
    if (!response.ok || !token.access_token) return json(502, { error: 'token_refresh_failed' })
    const patch = { encrypted_access_token: seal(token.access_token, c.TIKTOK_TOKEN_ENCRYPTION_KEY), encrypted_refresh_token: token.refresh_token ? seal(token.refresh_token, c.TIKTOK_TOKEN_ENCRYPTION_KEY) : connection.encrypted_refresh_token, access_token_expires_at: token.expires_in ? new Date(Date.now() + token.expires_in * 1000).toISOString() : null, refresh_token_expires_at: token.refresh_expires_in ? new Date(Date.now() + token.refresh_expires_in * 1000).toISOString() : connection.refresh_token_expires_at, scopes: String(token.scope || connection.scopes?.join(',') || '').split(',').filter(Boolean), status: 'CONNECTED', updated_at: new Date().toISOString() }
    await db(c, `nexus_tiktok_connections?id=eq.${connection.id}&user_id=eq.${encodeURIComponent(u.id)}&tenant_id=eq.${encodeURIComponent(u.tenant)}`, { method: 'PATCH', body: JSON.stringify(patch) })
    return json(200, { refreshed: true, expires_at: patch.access_token_expires_at, token_exposed: false })
  } catch (e) {
    return json(400, { error: e.message })
  }
}
