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

    let authUserId: string | null = null

    const existingUser = await findUserByEmail(admin, invitation.tester_email)
    if (existingUser?.id) {
      const { error: pwError } = await admin.auth.admin.updateUserById(existingUser.id, { password })
      if (pwError) return json({ error: "password_update_failed" }, 500)
      authUserId = existingUser.id
    } else {
      const { data: newUser, error: createError } = await admin.auth.admin.createUser({
        email: invitation.tester_email,
        password,
        email_confirm: true,
        data: {
          full_name: invitation.tester_name,
          testing_level: invitation.testing_level,
          role: "tester",
        },
      })
      if (createError) return json({ error: "auth_user_creation_failed" }, 500)
      authUserId = newUser?.user?.id || null
    }

    if (!authUserId) return json({ error: "auth_user_resolution_failed" }, 500)

    const tenantId = invitation.assigned_tenant_id || "goclear"
    const clientId = invitation.assigned_client_id || `gc_${authUserId.replaceAll("-", "")}`
    const nowIso = new Date().toISOString()

    const bootstrapError = await bootstrapClientPortal(admin, {
      authUserId,
      tenantId,
      clientId,
      testerName: invitation.tester_name,
      testerEmail: invitation.tester_email,
      testingLevel: invitation.testing_level,
      paymentMode: invitation.payment_mode,
      paymentOfferSlug: invitation.payment_offer_slug,
      nowIso,
    })
    if (bootstrapError) return json({ error: "portal_bootstrap_failed" }, 500)

    const { error: updateError } = await admin.from("tester_invitations").update({
      invitation_status: "accepted",
      accepted_at: nowIso,
      auth_user_id: authUserId,
      assigned_tenant_id: tenantId,
      assigned_client_id: clientId,
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

async function findUserByEmail(admin: ReturnType<typeof createClient>, email: string) {
  const needle = email.trim().toLowerCase()
  for (let page = 1; page <= 5; page += 1) {
    const { data, error } = await admin.auth.admin.listUsers({ page, perPage: 200 })
    if (error) throw error
    const match = data.users.find((user) => String(user.email || "").toLowerCase() === needle)
    if (match) return match
    if (data.users.length < 200) break
  }
  return null
}

type PortalBootstrap = {
  authUserId: string
  tenantId: string
  clientId: string
  testerName: string | null
  testerEmail: string
  testingLevel: string | null
  paymentMode: string | null
  paymentOfferSlug: string | null
  nowIso: string
}

async function bootstrapClientPortal(admin: ReturnType<typeof createClient>, input: PortalBootstrap) {
  const displayName = input.testerName || input.testerEmail
  const portalPayload = {
    membershipTier: input.paymentOfferSlug || "Invited Tester",
    subscriptionStatus: input.paymentMode || "test_mode",
    currentGoal: "Complete your Funding Readiness baseline",
    advisorName: "GoClear Review Team",
    nextReviewDate: "After document intake",
    testerInvitation: true,
    testingLevel: input.testingLevel,
  }

  const { error: membershipError } = await admin.from("tenant_memberships").upsert({
    tenant_id: input.tenantId,
    user_id: input.authUserId,
    role: "client",
    client_id: input.clientId,
    created_at: input.nowIso,
  }, { onConflict: "tenant_id,user_id" })
  if (membershipError) return membershipError

  const { error: profileError } = await admin.from("client_profiles").upsert({
    id: input.authUserId,
    tenant_id: input.tenantId,
    client_id: input.clientId,
    client_label: displayName,
    title: displayName,
    status: "onboarding",
    client_visible: true,
    approval_required: false,
    source: "tester_invitation",
    recommended_next_action: "Complete onboarding and upload your first readiness document.",
    payload: portalPayload,
    updated_at: input.nowIso,
  }, { onConflict: "id" })
  if (profileError) return profileError

  const scoreRows = [
    ["credit_profile", "Credit Readiness", "NEEDS MORE INFORMATION: upload a current credit report and complete the credit profile."],
    ["business_profile", "Business Foundation", "NEEDS MORE INFORMATION: complete the business profile baseline."],
    ["funding_readiness", "Funding Readiness", "NEEDS MORE INFORMATION: complete onboarding and document intake."],
    ["credit_repair", "Review Readiness", "NEEDS MORE INFORMATION: submit a readiness review request when your intake is complete."],
  ].map(([category, title, summary]) => ({
    id: `wave1-${input.clientId}-${category}`,
    tenant_id: input.tenantId,
    client_id: input.clientId,
    category,
    title,
    summary,
    status: "needs_more_information",
    score: 0,
    priority: "baseline",
    risk_level: "unknown",
    automation_level: "deterministic",
    client_visible: true,
    approval_required: false,
    source: "tester_invitation_acceptance",
    recommended_next_action: category === "funding_readiness"
      ? "Complete onboarding and upload the requested readiness documents."
      : "Provide the missing intake information.",
    payload: { calculationVersion: "wave1-baseline-v1", evidenceStatus: "needs_more_information" },
    updated_at: input.nowIso,
  }))
  const { error: scoreError } = await admin.from("readiness_scores").upsert(scoreRows, { onConflict: "id" })
  if (scoreError) return scoreError

  const taskRows = [
    ["1", "Complete your readiness onboarding", "Choose your goal and provide the business and credit profile basics.", "Business Foundation"],
    ["2", "Upload your first readiness document", "Add a synthetic or approved test document so GoClear can confirm document intake works.", "Document Intake"],
    ["3", "Request your readiness review", "Submit a review request after onboarding and document upload so the admin team can respond.", "Funding Readiness"],
  ].map(([rank, title, summary, readinessArea]) => ({
    id: `wave1-${input.clientId}-task-${rank}`,
    tenant_id: input.tenantId,
    client_id: input.clientId,
    category: "next_best_action",
    title,
    summary,
    status: "open",
    priority: rank,
    risk_level: "low",
    automation_level: "deterministic",
    client_visible: true,
    approval_required: false,
    source: "tester_invitation_acceptance",
    source_concept: readinessArea,
    recommended_next_action: summary,
    payload: { rank: Number(rank), readinessArea, evidenceRequired: rank !== "1" },
    updated_at: input.nowIso,
  }))
  const { error: taskError } = await admin.from("client_tasks").upsert(taskRows, { onConflict: "id" })
  return taskError
}
