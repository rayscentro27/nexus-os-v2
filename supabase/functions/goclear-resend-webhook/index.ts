import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const headers = { "Content-Type": "application/json" }
const json = (body: Record<string, unknown>, status = 200) => new Response(JSON.stringify(body), { status, headers })
const hex = (bytes: Uint8Array) => Array.from(bytes).map((b) => b.toString(16).padStart(2, "0")).join("")
function decodeBase64(value: string) { const raw = atob(value); return Uint8Array.from(raw, (c) => c.charCodeAt(0)) }
async function validSignature(payload: string, secret: string, id: string, timestamp: string, signatures: string) {
  if (!secret.startsWith("whsec_") || !id || !timestamp || !signatures) return false
  const timestampSeconds = Number(timestamp)
  if (!Number.isFinite(timestampSeconds) || Math.abs(Date.now() / 1000 - timestampSeconds) > 300) return false
  const key = await crypto.subtle.importKey("raw", decodeBase64(secret.slice(6)), { name: "HMAC", hash: "SHA-256" }, false, ["sign"])
  const expected = hex(new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${id}.${timestamp}.${payload}`))))
  const expectedBase64 = btoa(String.fromCharCode(...new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${id}.${timestamp}.${payload}`)))))
  return signatures.split(" ").some((part) => { const [version, value] = part.split(","); return version === "v1" && (value === expectedBase64 || value === expected) })
}
const eventMap: Record<string, string> = { "email.sent": "sent", "email.delivered": "delivered", "email.bounced": "bounced", "email.clicked": "clicked", "email.complained": "complained", "email.unsubscribed": "unsubscribed", "email.suppressed": "bounced" }

serve(async (req) => {
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405)
  const payload = await req.text()
  const id = req.headers.get("svix-id") || "", timestamp = req.headers.get("svix-timestamp") || "", signature = req.headers.get("svix-signature") || ""
  const secret = Deno.env.get("RESEND_WEBHOOK_SECRET") || ""
  if (!await validSignature(payload, secret, id, timestamp, signature)) return json({ error: "invalid_webhook_signature" }, 401)
  let event: any
  try { event = JSON.parse(payload) } catch { return json({ error: "invalid_json" }, 400) }
  const eventType = eventMap[String(event.type || "")]
  if (!eventType) return json({ ok: true, ignored: true })
  const data = event.data || {}
  const providerMessageId = String(data.email_id || data.id || "")
  if (!providerMessageId) return json({ error: "provider_message_id_missing" }, 400)
  const url = Deno.env.get("SUPABASE_URL") || "", serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || ""
  if (!url || !serviceKey) return json({ error: "server_configuration_missing" }, 503)
  const admin = createClient(url, serviceKey)
  const recipient = String(Array.isArray(data.to) ? data.to[0] || "" : data.to || "").trim().toLowerCase()
  const recipientHash = recipient ? hex(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(recipient)))) : null
  const { data: message } = await admin.from("marketing_email_messages").select("email_message_id,lead_id,recipient").eq("provider_message_id", providerMessageId).maybeSingle()
  const emailMessageId = message?.email_message_id || null
  const { data: inserted, error: eventError } = await admin.from("goclear_email_events").insert({ email_message_id: emailMessageId, provider: "resend", provider_message_id: providerMessageId, provider_event_id: id, event_type: eventType, recipient_hash: recipientHash, signature_verified: true, payload: event, occurred_at: event.created_at || new Date().toISOString() }).select("id").maybeSingle()
  if (eventError && !String(eventError.message || "").toLowerCase().includes("duplicate")) return json({ error: "event_persist_failed" }, 503)
  if (emailMessageId) {
    const update: Record<string, string> = {}
    if (eventType === "sent") update.send_status = "SENT"
    if (eventType === "delivered") update.delivery_status = "DELIVERED"
    if (eventType === "bounced") { update.delivery_status = "BOUNCED"; update.bounce_status = "BOUNCED" }
    if (eventType === "clicked") update.click_status = "CLICKED"
    if (eventType === "complained") update.delivery_status = "COMPLAINT"; if (eventType === "unsubscribed") update.unsubscribe_status = "UNSUBSCRIBED"
    await admin.from("marketing_email_messages").update(update).eq("email_message_id", emailMessageId)
    const { data: distribution } = await admin.from("marketing_distribution_records").select("distribution_id").eq("provider_object_id", providerMessageId).maybeSingle()
    if (distribution) await admin.from("marketing_distribution_records").update({ status: eventType === "delivered" ? "DELIVERED" : eventType.toUpperCase(), receipt_id: id, updated_at: new Date().toISOString() }).eq("distribution_id", distribution.distribution_id)
    if (["bounced", "complained", "unsubscribed"].includes(eventType) && recipientHash) await admin.from("goclear_email_suppressions").upsert({ recipient_hash: recipientHash, reason: eventType === "bounced" ? "bounced" : eventType === "complained" ? "complained" : "unsubscribed", source_event_id: inserted?.id || null }, { onConflict: "recipient_hash" })
    if (message?.lead_id) {
      const { data: lead } = await admin.from("goclear_leads").select("client_id").eq("id", message.lead_id).maybeSingle()
      if (lead?.client_id) { await admin.from("goclear_followup_jobs").update({ status: eventType === "delivered" ? "delivered" : eventType === "bounced" ? "failed" : "sent", updated_at: new Date().toISOString() }).eq("email_message_id", emailMessageId); await admin.rpc("goclear_refresh_beta_journey_projection", { p_client_id: lead.client_id }) }
    }
  }
  return json({ ok: true, event_type: eventType, provider_message_id: providerMessageId })
})
