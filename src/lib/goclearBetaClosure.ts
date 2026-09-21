import { supabase } from './supabaseClient'
import { resolveClientContextForCurrentUser } from './clientAuthContext'

export async function captureGoclearLead(input: { name?: string; email?: string; campaignId?: string; variant?: string; betaMode?: boolean }) {
  if (!supabase || !input.email) return { ok: false, error: 'lead_context_missing' } as const
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { ok: false, error: 'authentication_required' } as const
  const context = await resolveClientContextForCurrentUser()
  const { data, error } = await supabase.rpc('goclear_capture_lead', {
    p_email: input.email,
    p_name: input.name || null,
    p_campaign_id: input.campaignId || null,
    p_variant: input.variant || null,
    p_beta_mode: input.betaMode ?? true,
    p_auth_user_id: user.id,
    p_tenant_id: context?.tenantId || null,
    p_client_id: context?.clientId || null,
  })
  if (error) return { ok: false, error: error.message } as const
  return { ok: true, lead: data } as const
}

export async function persistUploadReceipt(input: { documentId: string; storageObject: string; category: string; processingStatus?: string; metadata?: Record<string, unknown> }) {
  if (!supabase) return { ok: false, error: 'supabase_not_configured' } as const
  const context = await resolveClientContextForCurrentUser()
  if (!context) return { ok: false, error: 'client_context_required' } as const
  const { data, error } = await supabase.from('goclear_upload_receipts').insert({
    client_id: context.clientId,
    tenant_id: context.tenantId,
    document_id: input.documentId,
    storage_object: input.storageObject,
    category: input.category,
    processing_status: input.processingStatus || 'uploaded',
    metadata: input.metadata || {},
  }).select('id').single()
  if (error) return { ok: false, error: error.message } as const
  return { ok: true, receiptId: data.id } as const
}

export async function persistClydeReceipt(input: { question: string; answer: string; status?: string; intent?: string; provider?: string; model?: string }) {
  if (!supabase) return { ok: false, error: 'supabase_not_configured' } as const
  const context = await resolveClientContextForCurrentUser()
  if (!context) return { ok: false, error: 'client_context_required' } as const
  const encoded = new TextEncoder().encode(`${context.clientId}|${input.question}|${input.answer}`)
  const digest = await crypto.subtle.digest('SHA-256', encoded)
  const inputContextHash = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('')
  const { data, error } = await supabase.from('goclear_clyde_receipts').insert({
    client_id: context.clientId,
    input_context_hash: inputContextHash,
    research_refs: ['readiness_rules_v1', 'tenant_scoped_client_context'],
    guidance: input.answer,
    provider: input.provider || 'client-ai-gateway',
    model: input.model || 'TIER_0',
    status: input.status || 'completed',
    metadata: { question: input.question, intent: input.intent || null },
  }).select('id').single()
  if (error) return { ok: false, error: error.message } as const
  return { ok: true, receiptId: data.id } as const
}

export async function persistClientReport(input: { readiness: any; clydeReceiptIds?: string[]; resourceRefs?: string[] }) {
  if (!supabase) return { ok: false, error: 'supabase_not_configured' } as const
  const context = await resolveClientContextForCurrentUser()
  if (!context) return { ok: false, error: 'client_context_required' } as const
  const readiness = input.readiness || {}
  const { data, error } = await supabase.from('goclear_client_reports').insert({
    client_id: context.clientId,
    tenant_id: context.tenantId,
    status: 'ready',
    readiness_summary: { state: readiness.state || null, score: readiness.overallScore || null, primary_blocker: readiness.primaryBlocker || null },
    priority_issues: readiness.primaryBlocker ? [readiness.primaryBlocker] : [],
    missing_items: readiness.outstandingRequirements || [],
    next_steps: readiness.nextBestAction ? [readiness.nextBestAction] : [],
    credit_repair_options: ['Managed credit-repair referral only if an approved provider path is configured.', 'Self-directed education and checklist with privacy guardrails.'],
    business_recommendations: readiness.tier1?.recommendedActions || [],
    funding_guidance: { text: 'Prepare evidence and request GoClear review; no funding approval is promised.', tier1: readiness.tier1?.status || null, tier2: readiness.tier2?.status || null },
    resource_refs: input.resourceRefs || [],
    clyde_receipt_ids: input.clydeReceiptIds || [],
  }).select('id').single()
  if (error) return { ok: false, error: error.message } as const
  return { ok: true, reportId: data.id } as const
}

export async function createGoclearReviewRequest(input: { title?: string; notes?: string; readiness: any }) {
  if (!supabase) return { ok: false, error: 'supabase_not_configured' } as const
  const context = await resolveClientContextForCurrentUser()
  if (!context) return { ok: false, error: 'client_context_required' } as const
  const { data, error } = await supabase.rpc('goclear_create_review_request', {
    p_tenant_id: context.tenantId,
    p_client_id: context.clientId,
    p_title: input.title || 'GoClear readiness review requested',
    p_notes: input.notes || null,
    p_readiness_snapshot: { state: input.readiness?.state || null, blocker: input.readiness?.primaryBlocker || null, outstanding: input.readiness?.outstandingRequirements || [] },
  })
  if (error) return { ok: false, error: error.message } as const
  const { data: followup, error: followupError } = await supabase.functions.invoke('goclear-followup-trigger', { body: { work_id: data?.id } })
  if (followupError || followup?.error) return { ok: false, error: followupError?.message || followup?.error || 'followup_trigger_failed', workId: data?.id } as const
  return { ok: true, workId: data?.id, followup } as const
}

export async function submitBetaFeedback(input: { offerClarity: number; funnelClarity: number; portalUsability: number; reportUsefulness: number; nextStepClarity: number; creditRepairChoiceClarity: number; affiliateResourceClarity: number; brokenAreas?: string; comments?: string }) {
  if (!supabase) return { ok: false, error: 'supabase_not_configured' } as const
  const context = await resolveClientContextForCurrentUser()
  if (!context) return { ok: false, error: 'client_context_required' } as const
  const { data, error } = await supabase.from('goclear_beta_feedback').insert({
    offer_clarity: input.offerClarity,
    funnel_clarity: input.funnelClarity,
    portal_usability: input.portalUsability,
    report_usefulness: input.reportUsefulness,
    next_step_clarity: input.nextStepClarity,
    credit_repair_choice_clarity: input.creditRepairChoiceClarity,
    affiliate_resource_clarity: input.affiliateResourceClarity,
    broken_areas: input.brokenAreas || null,
    comments: input.comments || null,
    client_id: context.clientId,
    tenant_id: context.tenantId,
    status: 'feedback_submitted',
  }).select('id').single()
  if (error) return { ok: false, error: error.message } as const
  return { ok: true, feedbackId: data.id } as const
}
