import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const headers = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Content-Type": "application/json",
}

function json(body: Record<string, unknown>, status = 200) {
  return new Response(JSON.stringify(body), { status, headers })
}

function safePath(value: unknown, fallback: string) {
  return typeof value === "string" && /^\/(?!\/)[a-zA-Z0-9/_?=&.-]{1,180}$/.test(value) ? value : fallback
}

function getEnv(name: string) {
  return Deno.env.get(name) || ""
}

function firstEnv(names: string[]) {
  return names.map(getEnv).find(Boolean) || ""
}

function resolveStripeRuntime() {
  const mode = getEnv("STRIPE_MODE") || "test"
  if (mode !== "test" && mode !== "live") return { ok: false as const, error: "stripe_mode_invalid" }
  const secret = mode === "live" ? firstEnv(["STRIPE_LIVE_SECRET_KEY", "STRIPE_SECRET_KEY"]) : firstEnv(["STRIPE_TEST_SECRET_KEY", "STRIPE_SECRET_KEY"])
  const expectedSecretPrefix = mode === "live" ? "sk_live_" : "sk_test_"
  if (!secret.startsWith(expectedSecretPrefix)) return { ok: false as const, error: mode === "live" ? "live_payment_not_configured" : "test_payment_not_configured" }
  const priceByOffer: Record<string, string> = {
    "readiness-review-97": mode === "live" ? firstEnv(["STRIPE_LIVE_PRICE_READINESS_REVIEW_97", "STRIPE_LIVE_PRICE_READINESS_REVIEW"]) : firstEnv(["STRIPE_TEST_PRICE_READINESS_REVIEW_97", "STRIPE_TEST_PRICE_READINESS_REVIEW"]),
  }
  const publicAppUrl = mode === "live" ? (getEnv("NEXUS_PUBLIC_APP_URL") || getEnv("PUBLIC_SITE_URL")) : (getEnv("NEXUS_PUBLIC_APP_URL") || getEnv("PUBLIC_SITE_URL") || "https://goclear.invalid")
  if (mode === "live" && !/^https:\/\/[^/]+/.test(publicAppUrl)) return { ok: false as const, error: "live_public_url_required" }
  return { ok: true as const, mode, secret, priceByOffer, publicAppUrl }
}

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers })
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405)

  const authHeader = req.headers.get("Authorization")
  if (!authHeader) return json({ error: "authentication_required" }, 401)

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || ""
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") || ""
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || ""
  const stripeRuntime = resolveStripeRuntime()
  if (!supabaseUrl || !anonKey || !serviceKey) return json({ error: "server_configuration_missing" }, 503)
  if (!stripeRuntime.ok) return json({ error: stripeRuntime.error }, 503)

  try {
    const body = await req.json()
    const offerSlug = String(body.offerSlug || "").trim()
    const termsAccepted = body.termsAccepted === true
    const termsVersion = String(body.termsVersion || "")
    const successPath = safePath(body.successPath, "/checkout/success")
    const cancelPath = safePath(body.cancelPath, "/checkout/cancelled")

    const authClient = createClient(supabaseUrl, anonKey, { global: { headers: { Authorization: authHeader } } })
    const { data: authData, error: authError } = await authClient.auth.getUser()
    if (authError || !authData.user) return json({ error: "unauthorized" }, 401)

    const admin = createClient(supabaseUrl, serviceKey)
    const { data: membership } = await admin.from("tenant_memberships").select("tenant_id,client_id").eq("user_id", authData.user.id).eq("role", "client").limit(1).maybeSingle()
    if (!membership?.tenant_id || !membership?.client_id) return json({ error: "client_context_required" }, 403)

    const { data: offer, error: offerError } = await admin.from("service_offers").select("*").eq("slug", offerSlug).eq("active", true).single()
    if (offerError || !offer || !termsAccepted || termsVersion !== offer.terms_version) return json({ error: "offer_terms_validation_failed" }, 400)
    const configuredPrice = stripeRuntime.priceByOffer[offerSlug]
    const stripePrice = configuredPrice || (stripeRuntime.mode === "test" ? String(offer.test_price_id || "") : "")
    if (!stripePrice || !String(stripePrice).startsWith("price_")) return json({ error: stripeRuntime.mode === "live" ? "live_price_not_configured" : "test_price_not_configured" }, 503)

    // A still-open order is reused. This prevents repeated clicks from creating
    // multiple paid fulfillment paths for the same client and offer.
    const { data: existing } = await admin.from("client_orders").select("id,order_number,status,provider_checkout_session_id").eq("auth_user_id", authData.user.id).eq("offer_id", offer.id).in("status", ["draft", "checkout_created", "payment_pending"]).limit(1).maybeSingle()
    if (existing?.provider_checkout_session_id) return json({ ok: true, order_id: existing.id, order_number: existing.order_number, status: existing.status, checkout_session_id: existing.provider_checkout_session_id })

    const orderId = crypto.randomUUID()
    const orderNumber = `GC-${new Date().toISOString().slice(0, 10).replaceAll("-", "")}-${orderId.replaceAll("-", "").slice(-12).toUpperCase()}`
    const { error: orderError } = await admin.from("client_orders").insert({
      id: orderId,
      tenant_id: membership.tenant_id,
      client_id: membership.client_id,
      auth_user_id: authData.user.id,
      offer_id: offer.id,
      order_number: orderNumber,
      status: "draft",
      amount_cents: Number(offer.price_cents),
      currency: "usd",
      payment_provider: "stripe",
      payment_status: "unpaid",
      fulfillment_status: "not_started",
      terms_version: offer.terms_version,
      terms_accepted_at: new Date().toISOString(),
      referral_code: typeof body.referralCode === "string" ? body.referralCode.slice(0, 80) : null,
      referral_source: typeof body.referralSource === "string" ? body.referralSource.slice(0, 120) : null,
    })
    if (orderError) return json({ error: "order_creation_failed" }, 500)

    const stripeParams = new URLSearchParams()
    stripeParams.set("mode", "payment")
    stripeParams.set("line_items[0][price]", String(stripePrice))
    stripeParams.set("line_items[0][quantity]", "1")
    const appBaseUrl = stripeRuntime.publicAppUrl
    stripeParams.set("success_url", `${new URL(successPath, appBaseUrl).toString()}?order=${orderId}`)
    stripeParams.set("cancel_url", `${new URL(cancelPath, appBaseUrl).toString()}?order=${orderId}`)
    stripeParams.set("customer_email", String(authData.user.email || ""))
    stripeParams.set("client_reference_id", orderId)
    stripeParams.set("metadata[order_id]", orderId)
    stripeParams.set("metadata[offer_id]", String(offer.id))
    stripeParams.set("metadata[client_id]", String(membership.client_id))
    stripeParams.set("metadata[stripe_mode]", stripeRuntime.mode)
    const stripeResponse = await fetch("https://api.stripe.com/v1/checkout/sessions", { method: "POST", headers: { Authorization: `Bearer ${stripeRuntime.secret}`, "Content-Type": "application/x-www-form-urlencoded" }, body: stripeParams, signal: AbortSignal.timeout(15000) })
    if (!stripeResponse.ok) {
      await admin.from("client_orders").update({ status: "payment_failed", payment_status: "checkout_creation_failed" }).eq("id", orderId)
      return json({ error: "checkout_creation_failed" }, 502)
    }
    const session = await stripeResponse.json()
    const { error: persistError } = await admin.from("client_orders").update({ status: "checkout_created", payment_status: "pending", provider_checkout_session_id: String(session.id || "") }).eq("id", orderId)
    if (persistError) {
      await admin.from("client_orders").delete().eq("id", orderId)
      return json({ error: "checkout_persistence_failed" }, 502)
    }
    const expectedSessionPrefix = stripeRuntime.mode === "live" ? "cs_live_" : "cs_test_"
    if (!String(session.id || "").startsWith(expectedSessionPrefix)) {
      await admin.from("client_orders").delete().eq("id", orderId)
      return json({ error: "checkout_environment_mismatch" }, 502)
    }
    return json({ ok: true, order_id: orderId, order_number: orderNumber, status: "checkout_created", checkout_session_id: session.id, checkout_url: session.url || null, mode: stripeRuntime.mode })
  } catch {
    return json({ error: "checkout_request_failed" }, 500)
  }
})
