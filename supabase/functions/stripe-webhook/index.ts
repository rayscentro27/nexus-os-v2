import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type, stripe-signature", "Content-Type": "application/json" }
const json = (body: Record<string, unknown>, status = 200) => new Response(JSON.stringify(body), { status, headers })

function hex(bytes: Uint8Array) { return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("") }
function bytesEqual(a: string, b: string) { if (a.length !== b.length) return false; let result = 0; for (let i = 0; i < a.length; i++) result |= a.charCodeAt(i) ^ b.charCodeAt(i); return result === 0 }

async function verifyStripeSignature(raw: string, signature: string, secret: string) {
  const parts = Object.fromEntries(signature.split(",").map((part) => part.split("=", 2)))
  const timestamp = Number(parts.t)
  const candidate = parts.v1 || ""
  if (!timestamp || !candidate || Math.abs(Date.now() / 1000 - timestamp) > 300) return false
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"])
  const digest = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${timestamp}.${raw}`))
  return bytesEqual(hex(new Uint8Array(digest)), candidate)
}

function safePayload(event: any) {
  const object = event?.data?.object || {}
  return { id: String(event?.id || "").slice(0, 120), type: String(event?.type || "").slice(0, 100), created: Number(event?.created || 0) || null, object_type: String(object.object || "").slice(0, 80), payment_status: String(object.payment_status || "").slice(0, 40), payment_intent: String(object.payment_intent || "").slice(0, 120), checkout_session: String(object.id || "").slice(0, 120), metadata_keys: Object.keys(object.metadata || {}).slice(0, 20) }

}

function getWebhookRuntime() {
  const mode = Deno.env.get("STRIPE_MODE") || "test"
  if (mode !== "test" && mode !== "live") return { ok: false as const, error: "stripe_mode_invalid" }
  const secret = mode === "live" ? (Deno.env.get("STRIPE_LIVE_WEBHOOK_SECRET") || Deno.env.get("STRIPE_WEBHOOK_SECRET") || "") : (Deno.env.get("STRIPE_TEST_WEBHOOK_SECRET") || Deno.env.get("STRIPE_WEBHOOK_SECRET") || "")
  if (!secret.startsWith("whsec_")) return { ok: false as const, error: mode === "live" ? "live_webhook_not_configured" : "test_webhook_not_configured" }
  return { ok: true as const, mode, secret }
}

function orderMatchesRuntime(order: any, mode: string) {
  const sessionId = String(order?.provider_checkout_session_id || "")
  const expected = mode === "live" ? "cs_live_" : "cs_test_"
  return sessionId.startsWith(expected)
}

function verifiedPaymentMatchesOrder(type: string, object: any, order: any, mode: string) {
  if (Boolean(object?.livemode) !== (mode === "live")) return false
  if (!orderMatchesRuntime(order, mode)) return false
  const metadata = object?.metadata || {}
  const metadataOrderId = String(metadata.order_id || object.client_reference_id || "")
  const metadataOfferId = String(metadata.offer_id || "")
  const metadataMode = String(metadata.stripe_mode || "")
  const amount = type === "checkout.session.completed" ? Number(object.amount_total) : Number(object.amount_received ?? object.amount)
  const sessionMatches = type !== "checkout.session.completed" || String(object.id || "") === String(order.provider_checkout_session_id || "")
  const modeMatches = !metadataMode || metadataMode === mode
  return metadataOrderId === String(order.id) && metadataOfferId === String(order.offer_id) && modeMatches && sessionMatches && amount === Number(order.amount_cents) && String(object.currency || "").toLowerCase() === String(order.currency || "usd").toLowerCase() && (type !== "checkout.session.completed" || object.payment_status === "paid")
}

serve(async (req) => {
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405)
  const runtime = getWebhookRuntime()
  if (!runtime.ok) return json({ error: runtime.error }, 503)
  const raw = await req.text()
  const signature = req.headers.get("Stripe-Signature") || ""
  if (!signature || !(await verifyStripeSignature(raw, signature, runtime.secret))) return json({ error: "invalid_signature" }, 400)
  let event: any
  try { event = JSON.parse(raw) } catch { return json({ error: "invalid_event" }, 400) }
  const providerEventId = String(event.id || "")
  if (!/^evt_[A-Za-z0-9_]+$/.test(providerEventId)) return json({ error: "event_id_required" }, 400)
  const supabaseUrl = Deno.env.get("SUPABASE_URL") || ""
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || ""
  if (!supabaseUrl || !serviceKey) return json({ error: "server_configuration_missing" }, 503)
  const admin = createClient(supabaseUrl, serviceKey)
  const payload = safePayload(event)
  const { data: prior } = await admin.from("payment_events").select("id,processed_status").eq("provider_event_id", providerEventId).maybeSingle()
  if (prior) return json({ ok: true, duplicate: true, processed_status: prior.processed_status })

  const object = event?.data?.object || {}
  const metadata = object.metadata || {}
  const orderId = String(metadata.order_id || object.client_reference_id || "")
  const { data: order } = orderId ? await admin.from("client_orders").select("id,client_id,offer_id,status,amount_cents,currency,terms_version,referral_code,referral_source,provider_checkout_session_id").eq("id", orderId).maybeSingle() : { data: null }
  const { data: eventRow, error: eventError } = await admin.from("payment_events").insert({ provider: "stripe", provider_event_id: providerEventId, event_type: String(event.type || "unknown").slice(0, 100), event_created_at: event.created ? new Date(Number(event.created) * 1000).toISOString() : null, order_id: order?.id || null, processed_status: "received", sanitized_payload: payload }).select("id").single()
  if (eventError) return json({ error: "event_record_failed" }, 500)
  if (!order) { await admin.from("payment_events").update({ processed_status: "rejected", error_code: "order_not_found", processed_at: new Date().toISOString() }).eq("id", eventRow.id); return json({ error: "order_not_found" }, 422) }

  const type = String(event.type || "")
  let update: Record<string, unknown> | null = null
  if (!orderMatchesRuntime(order, runtime.mode)) { await admin.from("payment_events").update({ processed_status: "rejected", error_code: "order_environment_mismatch", processed_at: new Date().toISOString() }).eq("id", eventRow.id); return json({ error: "order_environment_mismatch" }, 422) }
  if ((type === "checkout.session.completed" || type === "payment_intent.succeeded") && !verifiedPaymentMatchesOrder(type, object, order, runtime.mode)) { await admin.from("payment_events").update({ processed_status: "rejected", error_code: "payment_order_mismatch", processed_at: new Date().toISOString() }).eq("id", eventRow.id); return json({ error: "payment_order_mismatch" }, 422) }
  if (type === "checkout.session.completed" || type === "payment_intent.succeeded") update = { status: "paid", payment_status: "verified_paid", paid_at: new Date().toISOString(), provider_payment_intent_id: object.payment_intent || (object.id?.startsWith("pi_") ? object.id : null), fulfillment_status: "onboarding_required" }
  else if (type === "checkout.session.expired") update = { status: "expired", payment_status: "expired" }
  else if (type === "payment_intent.payment_failed") update = { status: "payment_failed", payment_status: "failed" }
  else if (type === "charge.refunded") update = { status: "refunded", payment_status: "refunded", refunded_at: new Date().toISOString() }
  else if (type === "charge.dispute.created") update = { status: "disputed", payment_status: "disputed" }
  if (update) await admin.from("client_orders").update(update).eq("id", order.id)
  if (type === "checkout.session.completed" || type === "payment_intent.succeeded") {
    const { data: existingFulfillment } = await admin.from("service_fulfillments").select("id").eq("order_id", order.id).maybeSingle()
    if (!existingFulfillment) await admin.from("service_fulfillments").insert({ order_id: order.id, client_id: order.client_id, offer_id: order.offer_id, fulfillment_status: "onboarding_required", approval_status: "pending", delivery_status: "not_ready" })
    if (order.referral_code) await admin.from("referral_attributions").insert({ referral_code: String(order.referral_code).slice(0, 80), referrer_type: "configured_partner", referrer_id: order.referral_source ? String(order.referral_source).slice(0, 120) : null, offer_id: order.offer_id, order_id: order.id, payment_status: "verified_paid", eligible_revenue_cents: Number(order.amount_cents || 0), nexus_commission_basis_bps: 0, referral_commission_basis_bps: 0, commission_status: "pending_approval", payout_status: "not_scheduled" })
  }
  await admin.from("payment_events").update({ processed_status: "processed", processed_at: new Date().toISOString() }).eq("id", eventRow.id)
  return json({ ok: true, duplicate: false, order_id: order.id, event_type: type })
})
