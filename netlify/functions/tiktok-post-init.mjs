import { config, json, userFromBearer, db, unseal, tiktok } from './_tiktok.mjs'

export async function handler(event) {
  try {
    if (event.httpMethod !== 'POST') return json(405, { error: 'method_not_allowed' })
    const c = config(); const u = await userFromBearer(event, c); const input = JSON.parse(event.body || '{}')
    const mode = input.mode === 'draft' ? 'draft' : 'direct'
    if (!input.video_url || !/^https:\/\//i.test(input.video_url)) return json(400, { error: 'verified_https_video_url_required' })
    if (mode === 'direct' && (!input.approval_id || input.privacy_level !== 'SELF_ONLY')) return json(403, { error: 'direct_post_requires_approval_and_self_only_privacy' })
    const rows = await db(c, `nexus_tiktok_connections?user_id=eq.${u.id}&tenant_id=eq.${encodeURIComponent(u.tenant)}&environment=eq.${c.runtimeEnv}&status=eq.CONNECTED&select=*&limit=1`)
    if (!rows?.[0]) return json(404, { error: 'tiktok_connection_not_found' })
    const path = mode === 'draft' ? '/v2/post/publish/inbox/video/init/' : '/v2/post/publish/video/init/'
    const body = mode === 'draft' ? { source_info: { source: 'PULL_FROM_URL', video_url: input.video_url } } : { post_info: { title: String(input.title || '').slice(0, 2200), privacy_level: 'SELF_ONLY', disable_comment: true, disable_duet: true, disable_stitch: true }, source_info: { source: 'PULL_FROM_URL', video_url: input.video_url } }
    const result = await tiktok(c, unseal(rows[0].encrypted_access_token, c.TIKTOK_TOKEN_ENCRYPTION_KEY), path, { method: 'POST', body: JSON.stringify(body) })
    const publishId = result.body?.data?.publish_id || null
    await db(c, 'nexus_tiktok_post_receipts', { method: 'POST', headers: { Prefer: 'return=minimal' }, body: JSON.stringify({ connection_id: rows[0].id, tenant_id: u.tenant, user_id: u.id, publish_id: publishId, action: mode === 'draft' ? 'UPLOAD_DRAFT' : 'DIRECT_POST', status: result.ok ? 'PASS_REAL' : 'FAILED', response_metadata: { mode, http_status: result.status, approval_id: input.approval_id || null, upload_url_returned: Boolean(result.body?.data?.upload_url) } }) })
    return json(result.ok ? 200 : 502, { mode, publish_id: publishId, upload_url: result.body?.data?.upload_url || null, status: result.ok ? 'READY_FOR_PRIVATE_TEST' : 'REVIEW_GATED', token_exposed: false })
  } catch (e) { return json(400, { error: e.message }) }
}
