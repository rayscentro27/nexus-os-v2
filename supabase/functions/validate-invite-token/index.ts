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
    if (!rawToken || rawToken.length < 10) return json({ error: "invalid_token" }, 400)

    const admin = createClient(supabaseUrl, serviceKey)

    // Accept both raw tokens (hash them) and token_hashes (use directly)
    let tokenHash: string
    if (/^[a-f0-9]{64}$/.test(rawToken)) {
      // Looks like a hex SHA-256 hash — use directly
      tokenHash = rawToken
    } else {
      // Treat as raw token — hash it
      tokenHash = await hashToken(rawToken)
    }

    const { data: invitation } = await admin
      .from("tester_invitations")
      .select("id, tester_name, tester_email, testing_level, invitation_status, expires_at, assigned_persona, assigned_client_id, payment_offer_slug, payment_mode, allowlisted_for_pilot, terms_version, consent_version, task_checklist_version")
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

    return json({
      ok: true,
      invitation: {
        id: invitation.id,
        tester_name: invitation.tester_name,
        testing_level: invitation.testing_level,
        assigned_persona: invitation.assigned_persona,
        assigned_client_id: invitation.assigned_client_id,
        payment_offer_slug: invitation.payment_offer_slug,
        payment_mode: invitation.payment_mode,
        allowlisted_for_pilot: invitation.allowlisted_for_pilot,
        expires_at: invitation.expires_at,
        terms_version: invitation.terms_version,
        consent_version: invitation.consent_version,
        task_checklist_version: invitation.task_checklist_version,
      },
    })
  } catch (err) {
    console.error("[validate-invite-token]", err)
    return json({ error: "internal_error" }, 500)
  }
})

async function hashToken(raw: string): Promise<string> {
  const data = new TextEncoder().encode(raw)
  const hash = await crypto.subtle.digest("SHA-256", data)
  return Array.from(new Uint8Array(hash)).map((b) => b.toString(16).padStart(2, "0")).join("")
}
