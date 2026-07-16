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
      .select("id, invitation_status, tester_email, tester_name, resend_count, expires_at, testing_level, token_hash")
      .eq("id", invitationId)
      .maybeSingle()

    if (!invitation) return json({ error: "invitation_not_found" }, 404)
    if (!["approved", "sent"].includes(invitation.invitation_status)) {
      return json({ error: "invalid_status_for_send" }, 400)
    }

    const appUrl = Deno.env.get("NEXUS_PUBLIC_APP_URL") || "https://goclear.invalid"
    const acceptanceUrl = `${appUrl}/tester/invite/${invitation.token_hash}`

    const emailPayload = {
      to: invitation.tester_email,
      template: "tester_invitation" as const,
      data: {
        testerName: invitation.tester_name,
        testingLevel: invitation.testing_level === "invited_test_mode" ? "Invited Test Mode" : invitation.testing_level,
        expiresAt: new Date(invitation.expires_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }),
        acceptanceUrl,
        stripeTestMode: invitation.testing_level === "invited_test_mode" ? "true" : "false",
        timeCommitment: "30-60 minutes",
      },
    }

    let providerResult: string = "preview_only"
    let providerMessageId: string | null = null

    try {
      const emailResponse = await fetch(`${supabaseUrl}/functions/v1/send-client-email`, {
        method: "POST",
        headers: {
          "Authorization": authHeader,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(emailPayload),
        signal: AbortSignal.timeout(15000),
      })

      if (emailResponse.ok) {
        const emailResult = await emailResponse.json()
        providerResult = emailResult.success ? "sent" : "failed"
        providerMessageId = emailResult.id || null
      } else {
        const errText = await emailResponse.text()
        console.error("[send-tester-invitation] email delivery failed:", errText)
        providerResult = "delivery_failed"
      }
    } catch (emailErr) {
      console.error("[send-tester-invitation] email function call failed:", emailErr)
      providerResult = "function_call_failed"
    }

    await admin.from("tester_invitations").update({
      invitation_status: "sent",
      resend_count: invitation.resend_count + 1,
      last_sent_at: new Date().toISOString(),
    }).eq("id", invitation.id)

    await admin.from("invitation_events").insert({
      invitation_id: invitation.id,
      event_type: invitation.invitation_status === "sent" ? "invitation_resent" : "invitation_sent",
      actor_admin_id: authData.user.id,
      metadata: {
        resend_count: invitation.resend_count + 1,
        provider_result: providerResult,
        provider_message_id: providerMessageId,
      },
    })

    await admin.from("invite_email_drafts").insert({
      invitation_id: invitation.id,
      template_name: "tester_invitation",
      to_email: invitation.tester_email,
      subject: "You're Invited to Test Nexus — GoClear",
      status: providerResult === "sent" ? "sent" : providerResult === "preview_only" ? "draft" : "failed",
      provider_message_id: providerMessageId,
      sent_at: providerResult === "sent" ? new Date().toISOString() : null,
      error_message: providerResult !== "sent" && providerResult !== "preview_only" ? providerResult : null,
    })

    return json({
      ok: true,
      resend_count: invitation.resend_count + 1,
      provider_result: providerResult,
      provider_message_id: providerMessageId,
    })
  } catch (err) {
    console.error("[send-tester-invitation]", err)
    return json({ error: "internal_error" }, 500)
  }
})
