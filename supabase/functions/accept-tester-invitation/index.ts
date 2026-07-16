import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Content-Type": "application/json",
}

function json(body: Record<string, unknown>, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: corsHeaders })
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders })
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405)

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || ""
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || ""
  if (!supabaseUrl || !serviceKey) return json({ error: "server_configuration_missing" }, 503)

  try {
    const body = await req.json()
    const rawToken = String(body.token || "").trim()
    const password = String(body.password || "")
    const consentAccepted = body.consentAccepted === true

    if (!rawToken || rawToken.length < 20) return json({ error: "invalid_token" }, 400)
    if (!password || password.length < 8) return json({ error: "password_too_short" }, 400)
    if (password.length > 128) return json({ error: "password_too_long" }, 400)
    if (!consentAccepted) return json({ error: "consent_required" }, 400)

    const tokenHash = await hashToken(rawToken)
    const admin = createClient(supabaseUrl, serviceKey)

    const { data: invitation } = await admin
      .from("tester_invitations")
      .select("*")
      .eq("token_hash", tokenHash)
      .maybeSingle()

    if (!invitation) return json({ error: "invitation_not_found" }, 404)
    if (invitation.invitation_status === "revoked") return json({ error: "invitation_revoked" }, 403)
    if (invitation.invitation_status === "expired") return json({ error: "invitation_expired" }, 410)
    if (invitation.invitation_status === "accepted") return json({ error: "invitation_already_accepted" }, 409)
    if (invitation.invitation_status === "completed") return json({ error: "invitation_completed" }, 409)
    if (new Date(invitation.expires_at) < new Date()) {
      await admin.from("tester_invitations").update({ invitation_status: "expired" }).eq("id", invitation.id)
      return json({ error: "invitation_expired" }, 410)
    }

    const anonKey = Deno.env.get("SUPABASE_ANON_KEY") || ""
    const authClient = createClient(supabaseUrl, anonKey)

    let authUserId: string | null = null

    const { data: existingUser } = await authClient.auth.admin.getUserByEmail(invitation.tester_email)
    if (existingUser?.user) {
      const { error: pwError } = await authClient.auth.admin.updateUserById(existingUser.user.id, { password })
      if (pwError) return json({ error: "password_update_failed" }, 500)
      authUserId = existingUser.user.id
    } else {
      const { data: newUser, error: createError } = await authClient.auth.admin.inviteUserByEmail(invitation.tester_email, {
        password,
        data: {
          full_name: invitation.tester_name,
          testing_level: invitation.testing_level,
          role: "tester",
        },
        GOTRUE_EXPIRES_IN: 86400 * 30,
      })
      if (createError) return json({ error: "auth_user_creation_failed" }, 500)
      authUserId = newUser?.user?.id || null
    }

    if (!authUserId) return json({ error: "auth_user_resolution_failed" }, 500)

    const { error: updateError } = await admin.from("tester_invitations").update({
      invitation_status: "accepted",
      accepted_at: new Date().toISOString(),
      auth_user_id: authUserId,
    }).eq("id", invitation.id)

    if (updateError) return json({ error: "invitation_acceptance_failed" }, 500)

    await admin.from("invitation_events").insert({
      invitation_id: invitation.id,
      event_type: "invitation_accepted",
      actor_email: invitation.tester_email,
      metadata: { auth_user_id: authUserId },
    })

    if (invitation.testing_level === "controlled_live_pilot" && invitation.allowlisted_for_pilot) {
      const { data: existingAllowlist } = await admin
        .from("payment_pilot_allowlist")
        .select("id")
        .eq("tester_invitation_id", invitation.id)
        .maybeSingle()

      if (!existingAllowlist) {
        await admin.from("payment_pilot_allowlist").insert({
          tester_invitation_id: invitation.id,
          tester_email: invitation.tester_email,
          auth_user_id: authUserId,
          enabled: true,
          allowed_offer_slug: invitation.payment_offer_slug || "real-payment-pilot-1",
          max_orders: 1,
          approved_by: invitation.invited_by_admin_id,
        })
      }
    }

    return json({ ok: true, auth_user_id: authUserId, invitation_id: invitation.id })
  } catch (err) {
    console.error("[accept-tester-invitation]", err)
    return json({ error: "internal_error" }, 500)
  }
})

async function hashToken(raw: string): Promise<string> {
  const data = new TextEncoder().encode(raw)
  const hash = await crypto.subtle.digest("SHA-256", data)
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, "0")).join("")
}
