import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "POST, OPTIONS", "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, x-supabase-api-version", "Content-Type": "application/json" }
const json = (body: Record<string, unknown>, status = 200) => new Response(JSON.stringify(body), { status, headers })

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers })
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405)
  const url = Deno.env.get("SUPABASE_URL") || "", serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "", resendKey = Deno.env.get("RESEND_API_KEY") || ""
  if (!url || !serviceKey || !resendKey) return json({ error: "server_configuration_missing" }, 503)
  const authHeader = req.headers.get("Authorization") || ""
  const auth = createClient(url, Deno.env.get("SUPABASE_ANON_KEY") || "", { global: { headers: { Authorization: authHeader } } })
  const { data: userData, error: authError } = await auth.auth.getUser()
  if (authError || !userData.user) return json({ error: "authentication_required" }, 401)
  const admin = createClient(url, serviceKey)
  const body = await req.json().catch(() => ({}))
  const workId = String(body.work_id || "")
  if (!workId) return json({ error: "work_id_required" }, 400)
  const { data: work, error: workError } = await admin.from("client_tasks").select("id,client_id,tenant_id,status,category").eq("id", workId).eq("category", "review_request").maybeSingle()
  if (workError || !work) return json({ error: "review_work_not_found" }, 404)
  const { data: membership } = await admin.from("tenant_memberships").select("client_id").eq("client_id", work.client_id).eq("tenant_id", work.tenant_id).eq("user_id", userData.user.id).eq("role", "client").maybeSingle()
  if (!membership) return json({ error: "client_context_required" }, 403)
  const { data: userRecord } = await admin.auth.admin.getUserById(userData.user.id)
  const recipient = String(userRecord.user?.email || userData.user.email || "").trim().toLowerCase()
  if (!recipient) return json({ error: "recipient_missing" }, 400)
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(recipient))
  const recipientHash = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("")
  const { data: suppression } = await admin.from("goclear_email_suppressions").select("id,reason").eq("recipient_hash", recipientHash).maybeSingle()
  if (suppression) {
    await admin.from("goclear_followup_jobs").update({ status: "blocked", failure_reason: "marketing_suppression", updated_at: new Date().toISOString() }).eq("work_id", workId)
    return json({ error: "followup_blocked_suppressed", suppression_id: suppression.id }, 409)
  }
  const emailMessageId = `goclear-followup-${crypto.randomUUID()}`
  const distributionId = `goclear-beta-followup-${crypto.randomUUID()}`
  const { data: lead } = await admin.from("goclear_leads").select("id,campaign_id,funnel_id").eq("client_id", work.client_id).order("created_at", { ascending: false }).limit(1).maybeSingle()
  const campaignId = lead?.campaign_id || "goclear-friends-beta"
  const funnelId = lead?.funnel_id || "goclear_funding_readiness_funnel_v1"
  const { error: messageError } = await admin.from("marketing_email_messages").insert({ email_message_id: emailMessageId, campaign_id: campaignId, funnel_id: funnelId, lead_id: lead?.id || null, recipient, segment: "controlled_beta", message_type: "NURTURE", subject: "Your GoClear readiness review request is received", body_ref: "goclear_beta_review_followup_v1", cta: "/client-v2/review", tracking_id: emailMessageId, send_status: "QUEUED", provider: "resend" })
  if (messageError) return json({ error: "message_record_failed" }, 503)
  await admin.from("marketing_distribution_records").insert({ distribution_id: distributionId, campaign_id: campaignId, funnel_id: funnelId, channel: "email", content_id: emailMessageId, provider: "resend", status: "QUEUED", retry_state: { trigger_event: "review_requested", work_id: workId } })
  await admin.from("goclear_followup_jobs").update({ status: "sending", email_message_id: emailMessageId, updated_at: new Date().toISOString() }).eq("work_id", workId)
  const html = `<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:24px"><h1>Your GoClear review request is received</h1><p>We received your readiness review request. Your report and current next steps remain available in the GoClear portal.</p><p><a href="https://goclearonline.cc/client-v2/review">Open your review</a></p><p style="font-size:12px;color:#667085">GoClear provides advisory guidance and does not promise funding approval.</p></div>`
  const providerResponse = await fetch("https://api.resend.com/emails", { method: "POST", headers: { Authorization: `Bearer ${resendKey}`, "Content-Type": "application/json" }, body: JSON.stringify({ from: Deno.env.get("RESEND_FROM_EMAIL") || Deno.env.get("RESEND_FROM") || "GoClear <notifications@goclearonline.cc>", to: [recipient], subject: "Your GoClear readiness review request is received", html }) })
  const provider = await providerResponse.json().catch(() => ({}))
  if (!providerResponse.ok || !provider.id) {
    await admin.from("goclear_followup_jobs").update({ status: "failed", failure_reason: "provider_send_failed", updated_at: new Date().toISOString() }).eq("work_id", workId)
    await admin.from("marketing_email_messages").update({ send_status: "FAILED" }).eq("email_message_id", emailMessageId)
    return json({ error: "provider_send_failed" }, 502)
  }
  await admin.from("marketing_email_messages").update({ send_status: "SENT", provider_message_id: provider.id, sent_at: new Date().toISOString() }).eq("email_message_id", emailMessageId)
  await admin.from("marketing_distribution_records").update({ status: "SENT", provider_object_id: provider.id, sent_or_published_at: new Date().toISOString(), updated_at: new Date().toISOString() }).eq("distribution_id", distributionId)
  await admin.from("goclear_email_events").insert({ email_message_id: emailMessageId, provider: "resend", provider_message_id: provider.id, event_type: "sent", recipient_hash: recipientHash, signature_verified: false, payload: { trigger_event: "review_requested", work_id: workId } })
  await admin.from("goclear_followup_jobs").update({ status: "sent", provider_message_id: provider.id, updated_at: new Date().toISOString() }).eq("work_id", workId)
  await admin.rpc("goclear_refresh_beta_journey_projection", { p_client_id: work.client_id })
  return json({ ok: true, work_id: workId, email_message_id: emailMessageId, distribution_id: distributionId, provider_message_id: provider.id })
})
