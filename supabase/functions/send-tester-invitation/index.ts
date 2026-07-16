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

  const authHeader = req.headers.get("Authorization")
  if (!authHeader) return json({ error: "authentication_required" }, 401)

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || ""
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || ""
  if (!supabaseUrl || !serviceKey) return json({ error: "server_configuration_missing" }, 503)

  try {
    const authClient = createClient(supabaseUrl, Deno.env.get("SUPABASE_ANON_KEY") || "", {
      global: { headers: { Authorization: authHeader } },
    })
    const { data: authData, error: authError } = await authClient.auth.getUser()
    if (authError || !authData.user) return json({ error: "unauthorized" }, 401)

    const admin = createClient(supabaseUrl, serviceKey)
    const { data: isAdmin } = await admin.rpc("nexus_is_active_admin")
    if (!isAdmin) return json({ error: "admin_required" }, 403)

    const body = await req.json()
    const invitationId = String(body.invitationId || "").trim()
    if (!invitationId) return json({ error: "invitation_id_required" }, 400)

    const { data: invitation } = await admin
      .from("tester_invitations")
      .select("id, invitation_status, tester_email, tester_name, resend_count")
      .eq("id", invitationId)
      .maybeSingle()

    if (!invitation) return json({ error: "invitation_not_found" }, 404)
    if (!["approved", "sent"].includes(invitation.invitation_status)) {
      return json({ error: "invalid_status_for_resend" }, 400)
    }

    await admin.from("tester_invitations").update({
      resend_count: invitation.resend_count + 1,
      last_sent_at: new Date().toISOString(),
    }).eq("id", invitation.id)

    await admin.from("invitation_events").insert({
      invitation_id: invitation.id,
      event_type: "invitation_resent",
      actor_admin_id: authData.user.id,
      metadata: { resend_count: invitation.resend_count + 1 },
    })

    return json({ ok: true, resend_count: invitation.resend_count + 1 })
  } catch (err) {
    console.error("[send-tester-invitation]", err)
    return json({ error: "internal_error" }, 500)
  }
})
