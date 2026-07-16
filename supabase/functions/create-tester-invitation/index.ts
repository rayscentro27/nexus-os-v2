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
    const testerName = String(body.testerName || "").trim()
    const testerEmail = String(body.testerEmail || "").trim().toLowerCase()
    const testingLevel = String(body.testingLevel || "invited_test_mode").trim()
    const assignedPersona = body.assignedPersona || null
    const assignedClientId = body.assignedClientId || null
    const assignedTenantId = body.assignedTenantId || "nexus"
    const maxSessions = Math.min(Math.max(Number(body.maxSessions) || 3, 1), 10)
    const taskChecklistVersion = String(body.taskChecklistVersion || "v1")
    const paymentOfferSlug = body.paymentOfferSlug || null
    const paymentMode = String(body.paymentMode || "test")
    const termsVersion = String(body.termsVersion || "readiness-services-v1")
    const expiresInDays = Math.min(Math.max(Number(body.expiresInDays) || 7, 1), 30)

    if (!testerName || testerName.length < 2) return json({ error: "tester_name_required" }, 400)
    if (!testerEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(testerEmail)) return json({ error: "valid_email_required" }, 400)
    if (!["synthetic_internal", "invited_test_mode", "controlled_live_pilot"].includes(testingLevel)) {
      return json({ error: "invalid_testing_level" }, 400)
    }
    if (!["test", "controlled_live_pilot", "public_live"].includes(paymentMode)) {
      return json({ error: "invalid_payment_mode" }, 400)
    }
    if (paymentMode === "public_live") return json({ error: "public_live_disabled" }, 400)

    const { data: controls } = await admin.from("payment_pilot_controls").select("invitations_enabled").eq("id", "singleton").maybeSingle()
    if (controls && !controls.invitations_enabled) return json({ error: "invitations_disabled" }, 403)

    const tokenBytes = new Uint8Array(32)
    crypto.getRandomValues(tokenBytes)
    const rawToken = Array.from(tokenBytes).map((b) => b.toString(16).padStart(2, "0")).join("")
    const tokenHash = await hashToken(rawToken)
    const tokenLastFour = rawToken.slice(-4)

    const expiresAt = new Date(Date.now() + expiresInDays * 24 * 60 * 60 * 1000).toISOString()

    const { data: invitation, error: insertError } = await admin.from("tester_invitations").insert({
      invited_by_admin_id: authData.user.id,
      tester_name: testerName,
      tester_email: testerEmail,
      testing_level: testingLevel,
      assigned_persona: assignedPersona,
      assigned_client_id: assignedClientId,
      assigned_tenant_id: assignedTenantId,
      invitation_status: "draft",
      token_hash: tokenHash,
      token_last_four: tokenLastFour,
      expires_at: expiresAt,
      max_sessions: maxSessions,
      task_checklist_version: taskChecklistVersion,
      build_commit: typeof body.buildCommit === "string" ? body.buildCommit.slice(0, 80) : null,
      fixture_version: typeof body.fixtureVersion === "string" ? body.fixtureVersion.slice(0, 40) : "v1",
      payment_offer_slug: paymentOfferSlug,
      payment_mode: paymentMode,
      terms_version: termsVersion,
    }).select("id, tester_name, tester_email, testing_level, invitation_status, token_last_four, expires_at, created_at").single()

    if (insertError) {
      if (insertError.code === "23505") return json({ error: "duplicate_active_invitation" }, 409)
      return json({ error: "invitation_creation_failed" }, 500)
    }

    await admin.from("invitation_events").insert({
      invitation_id: invitation.id,
      event_type: "invitation_created",
      actor_admin_id: authData.user.id,
      metadata: { testing_level: testingLevel, tester_email: testerEmail },
    })

    return json({ ok: true, invitation, acceptance_url: `/tester/invite/${rawToken}`, raw_token: rawToken })
  } catch (err) {
    console.error("[create-tester-invitation]", err)
    return json({ error: "internal_error" }, 500)
  }
})

async function hashToken(raw: string): Promise<string> {
  const data = new TextEncoder().encode(raw)
  const hash = await crypto.subtle.digest("SHA-256", data)
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, "0")).join("")
}
