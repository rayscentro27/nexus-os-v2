import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, apikey, content-type", "Content-Type": "application/json" }
const json = (body: Record<string, unknown>, status = 200) => new Response(JSON.stringify(body), { status, headers })

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers })
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405)
  const url = Deno.env.get("SUPABASE_URL") || "", serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "", resendKey = Deno.env.get("RESEND_API_KEY") || ""
  const authHeader = req.headers.get("Authorization") || ""
  if (!url || !serviceKey || !resendKey) return json({ error: "server_configuration_missing" }, 503)
  const auth = createClient(url, Deno.env.get("SUPABASE_ANON_KEY") || "", { global: { headers: { Authorization: authHeader } } })
  const { data: userData, error: authError } = await auth.auth.getUser()
  if (authError || !userData.user) return json({ error: "authentication_required" }, 401)
  const admin = createClient(url, serviceKey)
  const body = await req.json()
  const recipient = String(body.recipient || body.to || "").trim().toLowerCase()
  if (!recipient || !recipient.includes("@")) return json({ error: "valid_recipient_required" }, 400)
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(recipient))
  const recipientHash = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("")
  const { data: suppression, error: suppressionError } = await admin.from("goclear_email_suppressions").select("id,reason").eq("recipient_hash", recipientHash).maybeSingle()
  if (suppressionError) return json({ error: "suppression_check_failed" }, 503)
  if (suppression) return json({ error: "marketing_send_blocked_unsubscribed", suppression_id: suppression.id }, 409)
  const trackingId = String(body.tracking_id || crypto.randomUUID())
  const response = await fetch("https://api.resend.com/emails", { method: "POST", headers: { Authorization: `Bearer ${resendKey}`, "Content-Type": "application/json" }, body: JSON.stringify({ from: Deno.env.get("RESEND_FROM_EMAIL") || Deno.env.get("RESEND_FROM") || "GoClear <notifications@goclearonline.cc>", to: [recipient], subject: String(body.subject || "GoClear beta follow-up"), html: String(body.html || "<p>Your GoClear beta follow-up is ready.</p>") }) })
  const result = await response.json().catch(() => ({}))
  if (!response.ok || !result.id) return json({ error: "provider_send_failed" }, 502)
  await admin.from("goclear_email_events").insert({ email_message_id: trackingId, provider: "resend", provider_message_id: result.id, event_type: "sent", recipient_hash: recipientHash, payload: { message_type: "MARKETING" } })
  return json({ ok: true, tracking_id: trackingId, provider_message_id: result.id })
})
