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

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers })
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405)

  const authHeader = req.headers.get("Authorization")
  if (!authHeader) return json({ error: "authentication_required" }, 401)

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || ""
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") || ""
  const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || ""
  const stripeSecret = Deno.env.get("STRIPE_SECRET_KEY") || ""
  const stripeMode = Deno.env.get("STRIPE_MODE") || "test"
  if (!supabaseUrl || !anonKey || !serviceKey) return json({ error: "server_configuration_missing" }, 503)
  if (stripeMode !== "test" || !stripeSecret.startsWith("sk_test_")) return json({ error: "test_mode_required" }, 503)

  try {
    const body = await req.json()
    const offerSlug = String(body.offerSlug || "").trim()
    const invitationToken = String(body.invitationToken || "").trim()
    const termsAccepted = body.termsAccepted === true
    const termsVersion = String(body.termsVersion || "")

    if (!offerSlug) return json({ error: "offer_slug_required" }, 400)
    if (!invitationToken) return json({ error: "invitation_token_required" }, 400)
    if (!termsAccepted) return json({ error: "terms_not_accepted" }, 400)

    const authClient = createClient(supabaseUrl, anonKey, { global: { headers: { Authorization: authHeader } } })
    const { data: authData, error: authError } = await authClient.auth.getUser()
    if (authError || !authData.user) return json({ error: "unauthorized" }, 401)

    const admin = createClient(supabaseUrl, serviceKey)

    const { data: controls } = await admin.from("payment_pilot_controls").select("emergency_checkout_disabled, test_mode_purchases_enabled, controlled_live_pilot_enabled, public_live_enabled").eq("id", "singleton").maybeSingle()
    if (controls?.emergency_checkout_disabled) return json({ error: "checkout_emergency_disabled" }, 503)
    if (!controls?.test_mode_purchases_enabled) return json({ error: "test_purchases_disabled" }, 503)
    if (controls?.public_live_enabled) return json({ error: "public_live_disabled" }, 403)

    const tokenHash = await hashToken(invitationToken)
    const { data: invitation } = await admin
      .from("tester_invitations")
      .select("*")
      .eq("token_hash", tokenHash)
      .maybeSingle()

    if (!invitation) return json({ error: "invitation_not_found" }, 404)
    if (invitation.invitation_status !== "accepted") return json({ error: "invitation_not_accepted" }, 400)
    if (invitation.auth_user_id !== authData.user.id) return json({ error: "invitation_user_mismatch" }, 403)
    if (new Date(invitation.expires_at) < new Date()) return json({ error: "invitation_expired" }, 410)
    if (invitation.payment_mode !== "test") return json({ error: "test_mode_only" }, 400)

    const { data: offer } = await admin.from("service_offers").select("*").eq("slug", offerSlug).eq("active", true).maybeSingle()
    if (!offer) return json({ error: "offer_not_found" }, 404)
    if (!offer.test_price_id || !String(offer.test_price_id).startsWith("price_")) return json({ error: "test_price_not_configured" }, 503)
    if (termsVersion !== offer.terms_version) return json({ error: "terms_version_mismatch" }, 400)

    if (invitation.payment_offer_slug && invitation.payment_offer_slug !== offerSlug) {
      return json({ error: "offer_mismatch" }, 400)
    }

    const { data: existingOrder } = await admin
      .from("client_orders")
      .select("id, order_number, status, provider_checkout_session_id")
      .eq("auth_user_id", authData.user.id)
      .eq("offer_id", offer.id)
      .in("status", ["draft", "checkout_created", "payment_pending", "paid"])
      .limit(1)
      .maybeSingle()

    if (existingOrder?.status === "paid") return json({ error: "order_already_paid" }, 409)
    if (existingOrder?.provider_checkout_session_id) return json({ ok: true, order_id: existingOrder.id, order_number: existingOrder.order_number, checkout_session_id: existingOrder.provider_checkout_session_id })

    const { data: membership } = await admin.from("tenant_memberships").select("tenant_id, client_id").eq("user_id", authData.user.id).eq("role", "client").limit(1).maybeSingle()
    const tenantId = membership?.tenant_id || invitation.assigned_tenant_id || "nexus"
    const clientId = membership?.client_id || invitation.assigned_client_id || `tester-${authData.user.id.slice(0, 8)}`

    if (!membership) {
      const { error: memberError } = await admin.from("tenant_memberships").insert({
        tenant_id: tenantId,
        user_id: authData.user.id,
        role: "client",
        client_id: clientId,
      })
      if (memberError && memberError.code !== "23505") return json({ error: "membership_creation_failed" }, 500)
    }

    const orderId = crypto.randomUUID()
    const orderNumber = `GC-T-${new Date().toISOString().slice(0, 10).replaceAll("-", "")}-${orderId.replaceAll("-", "").slice(-12).toUpperCase()}`

    const { error: orderError } = await admin.from("client_orders").insert({
      id: orderId,
      tenant_id: tenantId,
      client_id: clientId,
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
    })
    if (orderError) return json({ error: "order_creation_failed" }, 500)

    const stripeParams = new URLSearchParams()
    stripeParams.set("mode", "payment")
    stripeParams.set("line_items[0][price]", String(offer.test_price_id))
    stripeParams.set("line_items[0][quantity]", "1")
    const appBaseUrl = Deno.env.get("NEXUS_PUBLIC_APP_URL") || "https://goclear.invalid"
    stripeParams.set("success_url", `${appBaseUrl}/checkout/success?order=${orderId}`)
    stripeParams.set("cancel_url", `${appBaseUrl}/checkout/cancelled?order=${orderId}`)
    stripeParams.set("customer_email", String(authData.user.email || ""))
    stripeParams.set("client_reference_id", orderId)
    stripeParams.set("metadata[order_id]", orderId)
    stripeParams.set("metadata[offer_id]", String(offer.id))
    stripeParams.set("metadata[client_id]", clientId)
    stripeParams.set("metadata[invitation_id]", invitation.id)
    stripeParams.set("metadata[payment_mode]", "test")

    const stripeResponse = await fetch("https://api.stripe.com/v1/checkout/sessions", {
      method: "POST",
      headers: { Authorization: `Bearer ${stripeSecret}`, "Content-Type": "application/x-www-form-urlencoded" },
      body: stripeParams,
      signal: AbortSignal.timeout(15000),
    })

    if (!stripeResponse.ok) {
      await admin.from("client_orders").update({ status: "payment_failed", payment_status: "checkout_creation_failed" }).eq("id", orderId)
      return json({ error: "checkout_creation_failed" }, 502)
    }

    const session = await stripeResponse.json()
    const { error: persistError } = await admin.from("client_orders").update({
      status: "checkout_created",
      payment_status: "pending",
      provider_checkout_session_id: String(session.id || ""),
    }).eq("id", orderId)

    if (persistError) {
      await admin.from("client_orders").delete().eq("id", orderId)
      return json({ error: "checkout_persistence_failed" }, 502)
    }

    await admin.from("invitation_events").insert({
      invitation_id: invitation.id,
      event_type: "test_checkout_started",
      actor_email: authData.user.email,
      metadata: { order_id: orderId, offer_slug: offerSlug },
    })

    return json({ ok: true, order_id: orderId, order_number: orderNumber, checkout_session_id: session.id, checkout_url: session.url || null, mode: "test" })
  } catch (err) {
    console.error("[create-invited-checkout]", err)
    return json({ error: "internal_error" }, 500)
  }
})

async function hashToken(raw: string): Promise<string> {
  const data = new TextEncoder().encode(raw)
  const hash = await crypto.subtle.digest("SHA-256", data)
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, "0")).join("")
}
