import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

const headers = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, apikey, content-type", "Content-Type": "application/json" }
const json = (body: Record<string, unknown>, status = 200) => new Response(JSON.stringify(body), { status, headers })
const MAX_DAILY_CALLS = 40
const MAX_SESSION_CALLS = 12
const ROLE_ESCAPE = /ignore (?:all|your) instructions|pretend (?:i am|to be) an admin|show me (?:other|all) clients|credentials|api key|refresh token|run hermes|change nexus|internal (?:state|tools)|general web search|search the web/i
const INTENTS = [
  ["MISSING_DOCUMENTS", /missing documents?|what documents|document checklist/i],
  ["DOCUMENT_UPLOAD_HELP", /upload|attach|file type|document help/i],
  ["DOCUMENT_RECEIVED", /document.*(received|status)|did you get/i],
  ["NEXT_STEP", /what should i do next|next step|what do i do/i],
  ["CREDIT_UTILIZATION", /utilization|balance usage/i],
  ["CREDIT_PROFILE_STATUS", /credit profile|credit status|credit report/i],
  ["FUNDING_READINESS", /funding readiness|ready for funding|funding ready/i],
  ["FUNDING_REQUIREMENTS", /funding requirements|what does funding need/i],
  ["BUSINESS_SETUP", /business setup|ein|entity|business profile/i],
  ["BUSINESS_BANKABILITY", /bankability|bank statements|business banking/i],
  ["CASE_STATUS", /case status|support case|ticket status/i],
  ["REVIEW_STATUS", /review status|what is goclear reviewing/i],
  ["BILLING_HELP", /billing|payment|receipt|charge/i],
  ["LOGIN_HELP", /login|sign in|password|account access/i],
  ["APPOINTMENT_HELP", /appointment|schedule|meeting/i],
  ["COMPLAINT", /complaint|unhappy|report a problem/i],
  ["CANCELLATION_REQUEST", /cancel|cancellation/i],
  ["ESCALATION_REQUEST", /human|representative|escalate|talk to someone/i],
  ["GENERAL_CREDIT_EDUCATION", /credit score|improve credit|credit education/i],
  ["GENERAL_FUNDING_EDUCATION", /how does funding|funding education|lender/i],
]
function intentOf(message: string) { return INTENTS.find(([, pattern]) => pattern.test(message))?.[0] || (/(guarantee|guaranteed).*(fund|approval|credit)/i.test(message) ? "FUNDING_READINESS" : "OUT_OF_SCOPE") }
function responseFor(intent: string, question: string, ctx: { profile: any; missing: string[]; docs: any[]; tier: string }) {
  if (/guarantee|guaranteed/i.test(question)) return "I can explain readiness and next steps, but no one can guarantee funding, approval, credit results, or a lender decision. Lenders and providers make those decisions using their own criteria."
  if (intent === "NEXT_STEP") return ctx.missing.length ? `Your next step is to complete: ${ctx.missing.slice(0, 4).join(', ')}. Once those items are ready, you can request a GoClear review.` : "Your next step is to review your current readiness tasks and request a GoClear review when the package is complete."
  if (intent === "MISSING_DOCUMENTS") return ctx.missing.length ? `Based on your current tenant-scoped readiness state, the missing items are: ${ctx.missing.slice(0, 6).join(', ')}.` : "I do not see a missing-document requirement in the current client record. You can still upload a document for GoClear review."
  if (intent === "DOCUMENT_UPLOAD_HELP" || intent === "DOCUMENT_RECEIVED") return "Use Documents in the client portal to upload one supported file at a time. The portal records the upload and shows when it is pending GoClear review; I will not claim a document was reviewed until the record says so."
  if (["FUNDING_READINESS", "FUNDING_REQUIREMENTS", "GENERAL_FUNDING_EDUCATION"].includes(intent)) return `Your current access tier is ${ctx.tier || 'the client tier'}. I can explain funding readiness and preparation, but paid funding execution requires ${ctx.tier === 'FREE_GUEST' ? 'payment or a service agreement' : 'the governed service workflow'}. No funding outcome is guaranteed.`
  if (["CREDIT_PROFILE_STATUS", "CREDIT_UTILIZATION", "GENERAL_CREDIT_EDUCATION"].includes(intent)) return "I can explain the credit information currently available in your client record and suggest educational next steps. I cannot promise a score change, deletion, or approval."
  if (["BUSINESS_SETUP", "BUSINESS_BANKABILITY"].includes(intent)) return "Review your Business Setup and Bankability sections, complete the visible requirements, and upload supporting documents through the protected portal. Recommendations are preparation guidance, not lender decisions."
  if (["CASE_STATUS", "REVIEW_STATUS", "BILLING_HELP", "LOGIN_HELP", "APPOINTMENT_HELP"].includes(intent)) return "I can help with the current account, review, billing, or appointment workflow. I found the request and will keep the response limited to your tenant-scoped portal state; contact GoClear review if a human decision is needed."
  if (intent === "OUT_OF_SCOPE") return "I’m Clyde, GoClear’s client advisor. I can help with your account, documents, readiness, business preparation, funding education, and support workflows."
  return "I can help with that within your GoClear client workflow, or create a human review request if the answer requires a specialist."
}
serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers })
  if (req.method !== "POST") return json({ error: "method_not_allowed" }, 405)
  const url = Deno.env.get("SUPABASE_URL") || "", serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "", anonKey = Deno.env.get("SUPABASE_ANON_KEY") || ""
  const authHeader = req.headers.get("Authorization") || ""
  if (!url || !serviceKey || !anonKey) return json({ error: "server_configuration_missing" }, 503)
  try {
    const auth = createClient(url, anonKey, { global: { headers: { Authorization: authHeader } } })
    const { data: authData, error: authError } = await auth.auth.getUser()
    if (authError || !authData.user) return json({ error: "authentication_required" }, 401)
    const body = await req.json(), question = String(body.message || "").trim().slice(0, 2000), sessionId = String(body.sessionId || "").slice(0, 120)
    if (!question) return json({ error: "message_required" }, 400)
    const admin = createClient(url, serviceKey)
    const { data: membership } = await admin.from("tenant_memberships").select("tenant_id,client_id,role").eq("user_id", authData.user.id).eq("role", "client").limit(1).maybeSingle()
    if (!membership?.tenant_id || !membership?.client_id) return json({ decision: "POLICY_DENY", reason: "client_context_required" }, 403)
    const { data: profile } = await admin.from("client_profiles").select("payload,status").eq("id", authData.user.id).maybeSingle()
    const { data: controls } = await admin.from("client_ai_controls").select("*").eq("tenant_id", membership.tenant_id).eq("client_id", membership.client_id).maybeSingle()
    const tier = String(controls?.access_tier || profile?.payload?.accessTier || "CLIENT")
    const mode = String(body.mode || "clyde").toLowerCase()
    if (controls?.client_ai_paused || controls?.guest_access_revoked) return json({ decision: "POLICY_DENY", reason: controls.client_ai_paused ? "client_ai_paused" : "guest_access_revoked", answer: "Client AI is temporarily unavailable for this account. Please use the portal support path." })
    if (mode === "customer_service" && controls?.customer_service_ai_enabled === false) return json({ decision: "POLICY_DENY", reason: "customer_service_ai_disabled", answer: "Customer Service AI is currently disabled for this account. Please use the portal support path." })
    if (mode !== "customer_service" && controls?.clyde_enabled === false) return json({ decision: "POLICY_DENY", reason: "clyde_disabled", answer: "Clyde is currently disabled for this account. Please contact GoClear support if you need help." })
    if (controls?.escalation_only_mode) return json({ decision: "POLICY_ESCALATE", reason: "escalation_only_mode", answer: "Your client AI is currently set to escalation-only mode. I’ve routed this request for human review." }, 200)
    const dailyLimit = Number(controls?.token_daily_limit ?? MAX_DAILY_CALLS)
    const sessionLimit = Number(controls?.session_limit ?? MAX_SESSION_CALLS)
    const today = new Date().toISOString().slice(0, 10)
    const { data: usage } = await admin.from("client_ai_usage").select("call_count").eq("user_id", authData.user.id).eq("request_date", today).maybeSingle()
    if ((usage?.call_count || 0) >= dailyLimit) return json({ decision: "POLICY_DENY", reason: "daily_client_ai_limit_reached" }, 429)
    if (sessionId) {
      const { count: sessionCalls } = await admin.from("client_ai_conversations").select("id", { count: "exact", head: true }).eq("user_id", authData.user.id).eq("session_id", sessionId).gte("created_at", `${today}T00:00:00.000Z`)
      if ((sessionCalls || 0) >= sessionLimit) return json({ decision: "POLICY_DENY", reason: "session_client_ai_limit_reached" }, 429)
    }
    const intent = intentOf(question)
    let decision = "POLICY_ALLOW", owner = "CUSTOMER_SERVICE", priority = "normal"
    if (ROLE_ESCAPE.test(question)) decision = "POLICY_DENY"
    else if (/(start|begin|process|apply).*(funding|application)|paid funding|concierge/i.test(question)) decision = "POLICY_REQUIRE_PAYMENT"
    else if (["COMPLAINT", "CANCELLATION_REQUEST", "ESCALATION_REQUEST"].includes(intent)) { decision = "POLICY_ESCALATE"; owner = intent === "COMPLAINT" || intent === "CANCELLATION_REQUEST" ? "CUSTOMER_SERVICE" : "RAY_REVIEW"; priority = intent === "COMPLAINT" ? "high" : "normal" }
    const { data: docs } = await admin.from("client_documents").select("id,category,status,title").eq("client_id", membership.client_id).limit(100)
    const { data: tasks } = await admin.from("client_tasks").select("title,status").eq("client_id", membership.client_id).eq("client_visible", true).limit(100)
    const missing = (tasks || []).filter((t: any) => ["missing", "open", "pending"].includes(String(t.status).toLowerCase())).map((t: any) => String(t.title || "required task"))
    let answer = decision === "POLICY_DENY" ? "I can’t provide internal credentials, other clients’ information, company controls, or unrestricted web assistance. I can help with your own GoClear account and readiness workflow." : decision === "POLICY_REQUIRE_PAYMENT" ? "That is the paid funding-process boundary. Your current readiness access remains available, but funding execution requires verified payment or a service agreement." : responseFor(intent, question, { profile, missing, docs: docs || [], tier })
    if (decision === "POLICY_ESCALATE") {
      const escalation = await admin.from("client_ai_escalations").insert({ tenant_id: membership.tenant_id, client_id: membership.client_id, user_id: authData.user.id, intent, question, known_facts: { access_tier: tier, profile_status: profile?.status || null }, missing_facts: [], recommended_owner: owner, priority }).select("id").single()
      answer = `I’ve routed this to ${owner === "RAY_REVIEW" ? "human review" : "Customer Service"}. Your request is recorded; no external action was taken automatically.`
      if (escalation.error) answer = "I can route this to a human, but the escalation record is temporarily unavailable. Please use Request human review in the portal."
    }
    await admin.from("client_ai_conversations").insert({ tenant_id: membership.tenant_id, client_id: membership.client_id, user_id: authData.user.id, session_id: sessionId || null, intent, user_message: question, assistant_message: answer, policy_decision: decision, model_tier: "TIER_0", estimated_cost_class: "NEAR_ZERO" })
    await admin.from("client_ai_usage").upsert({ tenant_id: membership.tenant_id, client_id: membership.client_id, user_id: authData.user.id, request_date: today, call_count: (usage?.call_count || 0) + 1, last_request_at: new Date().toISOString() }, { onConflict: "user_id,request_date" })
    return json({ decision, intent, answer, data_scope: "OWN_CLIENT_SUPABASE_SUMMARY", model_tier: "TIER_0", estimated_cost_class: "NEAR_ZERO", session_id: sessionId || null, current_state: { access_tier: tier, visible_document_count: docs?.length || 0, open_task_count: missing.length } })
  } catch (error) { console.error("[client-ai-gateway]", error); return json({ error: "client_ai_unavailable" }, 500) }
})
