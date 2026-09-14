import { config, db, json, unseal, userFromBearer } from './_tiktok.mjs'

export async function handler(event) {
  try {
    if (event.httpMethod !== 'POST') return json(405, { error: 'method_not_allowed' })
    const c = config()
    const u = await userFromBearer(event, c)
    const rows = await db(c, `nexus_tiktok_connections?user_id=eq.${encodeURIComponent(u.id)}&tenant_id=eq.${encodeURIComponent(u.tenant)}&environment=eq.${c.runtimeEnv}&status=eq.CONNECTED&select=*&limit=1`)
    const connection = rows?.[0]
    if (!connection) return json(404, { error: 'tiktok_connection_not_found' })
    const accessToken = unseal(connection.encrypted_access_token, c.TIKTOK_TOKEN_ENCRYPTION_KEY)
    const response = await fetch('https://open.tiktokapis.com/v2/oauth/revoke/', { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded', 'cache-control': 'no-cache' }, body: new URLSearchParams({ client_key: c.TIKTOK_CLIENT_KEY, client_secret: c.TIKTOK_CLIENT_SECRET, token: accessToken }) })
    if (!response.ok) return json(502, { error: 'tiktok_revoke_failed' })
    await db(c, `nexus_tiktok_connections?id=eq.${connection.id}&user_id=eq.${encodeURIComponent(u.id)}&tenant_id=eq.${encodeURIComponent(u.tenant)}&environment=eq.${c.runtimeEnv}`, { method: 'PATCH', body: JSON.stringify({ status: 'DISCONNECTED', revoked_at: new Date().toISOString(), updated_at: new Date().toISOString() }) })
    await db(c, 'nexus_tiktok_post_receipts', { method: 'POST', headers: { Prefer: 'return=minimal' }, body: JSON.stringify({ connection_id: connection.id, tenant_id: u.tenant, user_id: u.id, action: 'DISCONNECT', status: 'PASS_REAL', response_metadata: { revoked: true } }) })
    return json(200, { disconnected: true, token_exposed: false })
  } catch (e) {
    return json(400, { error: e.message })
  }
}
