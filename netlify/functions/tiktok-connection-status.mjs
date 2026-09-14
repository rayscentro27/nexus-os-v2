import { config, dbAsUser, json, userFromBearer } from './_tiktok.mjs'

export async function handler(event) {
  try {
    const c = config({ persistence: false })
    const u = await userFromBearer(event, c)
    const rows = await dbAsUser(c, u, `nexus_tiktok_connections?user_id=eq.${encodeURIComponent(u.id)}&tenant_id=eq.${encodeURIComponent(u.tenant)}&environment=eq.${c.runtimeEnv}&select=id,open_id,environment,scopes,status,access_token_expires_at,refresh_token_expires_at,created_at,updated_at,revoked_at&order=updated_at.desc&limit=1`)
    const connection = rows?.[0] || null
    return json(200, { connected: Boolean(connection && connection.status !== 'DISCONNECTED'), environment: c.runtimeEnv, connection })
  } catch (e) {
    return json(400, { error: e.message })
  }
}
