import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, apikey, content-type", "Content-Type": "application/json" }
const json = (body: Record<string, unknown>, status = 200) => new Response(JSON.stringify(body), { status, headers })
const allowed = ['clyde_enabled','customer_service_ai_enabled','access_tier','token_daily_limit','session_limit','expensive_call_limit','escalation_only_mode','client_ai_paused','guest_access_revoked','convert_to_paid_workflow']
serve(async req => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers })
  if (req.method !== 'POST') return json({ error: 'method_not_allowed' }, 405)
  const url = Deno.env.get('SUPABASE_URL') || '', serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || '', anonKey = Deno.env.get('SUPABASE_ANON_KEY') || ''
  const authHeader = req.headers.get('Authorization') || ''
  try {
    const auth = createClient(url, anonKey, { global: { headers: { Authorization: authHeader } } })
    const { data: userData } = await auth.auth.getUser()
    if (!userData.user) return json({ error: 'authentication_required' }, 401)
    const admin = createClient(url, serviceKey)
    const { data: adminUser } = await admin.from('admin_users').select('id').eq('id', userData.user.id).eq('active', true).maybeSingle()
    if (!adminUser) return json({ error: 'admin_required' }, 403)
    const body = await req.json(), clientId = String(body.client_id || ''), tenantId = String(body.tenant_id || '')
    if (!clientId || !tenantId) return json({ error: 'client_context_required' }, 400)
    const { data: member } = await admin.from('tenant_memberships').select('user_id,client_id,tenant_id').eq('tenant_id', tenantId).eq('client_id', clientId).eq('role', 'client').limit(1).maybeSingle()
    if (!member) return json({ error: 'client_not_found' }, 404)
    const { data: current } = await admin.from('client_ai_controls').select('*').eq('tenant_id', tenantId).eq('client_id', clientId).maybeSingle()
    if (body.action === 'get') return json({ controls: current || { tenant_id: tenantId, client_id: clientId, user_id: member.user_id, clyde_enabled: true, customer_service_ai_enabled: true, access_tier: 'CLIENT', token_daily_limit: 40, session_limit: 12, expensive_call_limit: 0, escalation_only_mode: false, client_ai_paused: false, guest_access_revoked: false, convert_to_paid_workflow: false } })
    const updates: Record<string, unknown> = { tenant_id: tenantId, client_id: clientId, user_id: member.user_id, updated_by: userData.user.id, updated_at: new Date().toISOString() }
    for (const key of allowed) if (Object.prototype.hasOwnProperty.call(body, key)) updates[key] = body[key]
    const { data, error } = await admin.from('client_ai_controls').upsert(updates, { onConflict: 'tenant_id,client_id' }).select('*').single()
    if (error) return json({ error: 'controls_update_failed' }, 500)
    if (updates.guest_access_revoked === true) await admin.from('guest_invitations').update({ status: 'REVOKED', revoked_at: new Date().toISOString() }).eq('user_id', member.user_id).is('used_at', null)
    return json({ controls: data })
  } catch (_error) { return json({ error: 'controls_unavailable' }, 500) }
})
