import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, apikey, content-type", "Content-Type": "application/json" }
const json = (body: Record<string, unknown>, status = 200) => new Response(JSON.stringify(body), { status, headers })

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers })
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405)
  const url = Deno.env.get("SUPABASE_URL") || "", serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || ""
  if (!url || !serviceKey) return json({ error: "server_configuration_missing" }, 503)
  try {
    const body = await req.json(), token = String(body.token || "").trim(), password = String(body.password || "")
    if (!/^[a-f0-9]{64}$/.test(token)) return json({ error: "invalid_token" }, 400)
    if (password.length < 8 || password.length > 128) return json({ error: "password_invalid" }, 400)
    if (body.consentAccepted !== true) return json({ error: "consent_required" }, 400)
    const admin = createClient(url, serviceKey), tokenHash = await hash(token)
    const { data: invite } = await admin.from("guest_invitations").select("*").eq("token_hash", tokenHash).maybeSingle()
    if (!invite) return json({ error: "invitation_not_found" }, 404)
    if (invite.status === "REVOKED" || invite.revoked_at) return json({ error: "invitation_revoked" }, 403)
    if (invite.status === "EXPIRED" || new Date(invite.expires_at) <= new Date()) { await admin.from("guest_invitations").update({ status: "EXPIRED" }).eq("id", invite.id); return json({ error: "invitation_expired" }, 410) }
    if (invite.used_at || ["SIGNED_UP", "ONBOARDING", "FREE_ACTIVE", "CONVERTED_TO_PAID"].includes(invite.status)) return json({ error: "invitation_already_used" }, 409)
    const { data: users } = await admin.auth.admin.listUsers({ page: 1, perPage: 1000 })
    const existing = users?.users.find((u) => String(u.email || "").toLowerCase() === invite.email)
    const authResult = existing ? await admin.auth.admin.updateUserById(existing.id, { password }) : await admin.auth.admin.createUser({ email: invite.email, password, email_confirm: true, user_metadata: { full_name: invite.name, access_tier: "FREE_GUEST" } })
    if (authResult.error) return json({ error: "account_creation_failed" }, 500)
    const userId = existing?.id || authResult.data.user?.id
    if (!userId) return json({ error: "account_creation_failed" }, 500)
    const clientId = `guest_${userId.replaceAll("-", "")}`
    const now = new Date().toISOString()
    const membership = await admin.from("tenant_memberships").upsert({ tenant_id: invite.tenant_id, user_id: userId, role: "client", client_id: clientId }, { onConflict: "tenant_id,user_id" })
    const profile = await admin.from("client_profiles").upsert({ id: userId, tenant_id: invite.tenant_id, client_id: clientId, client_label: invite.name, title: invite.name, status: "onboarding", client_visible: true, approval_required: false, source: "guest_invitation", payload: { accessTier: "FREE_GUEST", paymentBypassScope: "ONBOARDING_AND_READINESS", fundingGate: "PAYMENT_OR_SERVICE_AGREEMENT_REQUIRED" }, updated_at: now }, { onConflict: "id" })
    if (membership.error || profile.error) return json({ error: "portal_binding_failed" }, 500)
    const updated = await admin.from("guest_invitations").update({ status: "ONBOARDING", used_at: now, user_id: userId }).eq("id", invite.id).is("used_at", null).select("id")
    if (updated.error) return json({ error: "invitation_finalize_failed" }, 500)
    if (!updated.data?.length) return json({ error: "invitation_already_used" }, 409)
    await admin.from("customer_communications").insert({ tenant_id: invite.tenant_id, client_id: clientId, template_id: "guest_welcome", trigger: "GUEST_SIGNUP", recipient: invite.email, sent_at: null, status: "QUEUED", related_invite_id: invite.id, metadata: { access_tier: "FREE_GUEST" } })
    await admin.from("invitation_events").insert({ invitation_id: null, guest_invitation_id: invite.id, event_type: "guest_invitation_signed_up", actor_email: invite.email, metadata: { guest_invitation_id: invite.id, user_id: userId, access_tier: "FREE_GUEST" } })
    return json({ ok: true, user_id: userId, client_id: clientId, access_tier: "FREE_GUEST", funding_gate: invite.funding_gate })
  } catch (error) { console.error("[accept-guest-invitation]", error); return json({ error: "internal_error" }, 500) }
})

async function hash(value: string) { const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)); return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("") }
