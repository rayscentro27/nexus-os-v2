import { supabase } from './supabaseClient'

type SupabaseLike = NonNullable<typeof supabase>

export interface FeedbackRow {
  id: string
  persona: string
  page_route: string | null
  workflow_step: string | null
  issue_title: string
  issue_description: string | null
  expected_behavior: string | null
  actual_behavior: string | null
  severity: string
  reproducibility: string | null
  evidence_reference: string | null
  browser_device: string | null
  fixture_version: string | null
  build_commit: string | null
  status: string
  ray_review_item_id: string | null
}

const SEVERITY_TO_RISK: Record<string, string> = {
  blocker: 'critical',
  high: 'high',
  medium: 'medium',
  low: 'low',
  cosmetic: 'low',
}

function sanitize(text: unknown, maxLen = 2000): string {
  if (text === null || text === undefined) return ''
  return String(text).replace(/[<>]/g, '').replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, maxLen)
}

function parsePayload(value: unknown): Record<string, any> {
  if (!value) return {}
  if (typeof value === 'object') return value as Record<string, any>
  try { return JSON.parse(String(value)) || {} } catch { return {} }
}

async function linkFeedback(client: SupabaseLike, feedbackId: string, rayReviewId: string) {
  return client
    .from('tester_feedback')
    .update({ ray_review_item_id: rayReviewId, status: 'in_review', updated_at: new Date().toISOString() })
    .eq('id', feedbackId)
}

async function findExistingRayReview(client: SupabaseLike, feedbackId: string) {
  const { data: payloadRows } = await Promise.resolve(
    client
      .from('task_requests')
      .select('id, payload')
      .eq('task_type', 'ray_review_item')
      .limit(200)
  ).catch(() => ({ data: null }))

  if (!Array.isArray(payloadRows)) return null
  const duplicate = payloadRows.find((row: any) => parsePayload(row.payload).feedback_record_id === feedbackId)
  return duplicate?.id ? String(duplicate.id) : null
}

export async function routeFeedbackToRayReview(feedback: FeedbackRow, client: SupabaseLike | null = supabase): Promise<{ ok: boolean; rayReviewId?: string; error?: string }> {
  if (!client) return { ok: false, error: 'Supabase not configured' }
  const severity = sanitize(feedback.severity, 20).toLowerCase()
  if (severity !== 'blocker' && severity !== 'high') {
    return { ok: false, error: 'Only blocker/high feedback is routed to Ray Review' }
  }

  if (feedback.ray_review_item_id) {
    return { ok: true, rayReviewId: sanitize(feedback.ray_review_item_id, 120) }
  }

  const duplicateId = await findExistingRayReview(client, feedback.id)
  if (duplicateId) {
    const { error: linkError } = await linkFeedback(client, feedback.id, duplicateId)
    if (linkError) return { ok: false, error: `Existing Ray Review found but feedback link failed: ${linkError.message}` }
    return { ok: true, rayReviewId: duplicateId }
  }

  const commit = feedback.build_commit || import.meta.env?.VITE_BUILD_COMMIT || 'unknown'
  const feedbackId = sanitize(feedback.id, 120)
  const persona = sanitize(feedback.persona, 20).toLowerCase()

  const payload = {
    title: `[${severity.toUpperCase()}] Persona ${persona.toUpperCase()}: ${sanitize(feedback.issue_title, 240)}`,
    category: 'tester_feedback',
    riskLevel: SEVERITY_TO_RISK[severity] || 'medium',
    externalAction: false,
    recommendation: `Tester-reported ${severity} issue requiring Ray review.`,
    source: `tester_feedback:${feedbackId}`,
    data_source: 'tester_feedback',
    synthetic: true,
    feedback_record_id: feedbackId,
    persona,
    page_route: sanitize(feedback.page_route, 240),
    workflow_step: sanitize(feedback.workflow_step, 240),
    issue_title: sanitize(feedback.issue_title, 240),
    issue_description: sanitize(feedback.issue_description),
    expected_behavior: sanitize(feedback.expected_behavior),
    actual_behavior: sanitize(feedback.actual_behavior),
    severity,
    reproducibility: sanitize(feedback.reproducibility, 40),
    browser_device: sanitize(feedback.browser_device, 120),
    fixture_version: sanitize(feedback.fixture_version, 40),
    build_commit: sanitize(commit, 120),
    evidence_reference: sanitize(feedback.evidence_reference, 240),
    proposed_owner: 'ray',
    proposed_next_action: 'Review the reported issue and decide on resolution.',
    status_required: 'pending',
    requires_ray_review: true,
    auto_approve: false,
    auto_execute: false,
  }

  const { data: inserted, error: insertError } = await client
    .from('task_requests')
    .insert({
      task_type: 'ray_review_item',
      requested_by: 'tester_feedback',
      sensitivity: severity === 'blocker' ? 'internal_summary' : 'public',
      assigned_worker_type: 'manual_ray_review',
      hermes_visibility: 'status_only',
      allowed_data_scope: ['synthetic_tester_feedback_summary'],
      forbidden_data: ['client_pii', 'credentials', 'raw_credit_report_contents', 'external_actions'],
      status: 'requested',
      payload,
    })
    .select('id')
    .single()

  if (insertError || !inserted) {
    // The unique partial index is the final race-safe idempotency guard. If a
    // concurrent click won the insert, recover the existing Ray Review item.
    if ((insertError as any)?.code === '23505') {
      const concurrentId = await findExistingRayReview(client, feedback.id)
      if (concurrentId) {
        const { error: linkError } = await linkFeedback(client, feedback.id, concurrentId)
        if (!linkError) return { ok: true, rayReviewId: concurrentId }
      }
    }
    return { ok: false, error: `Failed to create Ray Review item: ${insertError?.message || 'unknown'}` }
  }

  const { error: linkError } = await linkFeedback(client, feedback.id, String(inserted.id))
  if (linkError) return { ok: false, rayReviewId: String(inserted.id), error: `Ray Review created but feedback link failed: ${linkError.message}` }

  return { ok: true, rayReviewId: String(inserted.id) }
}

export async function routeAllBlockerHighFeedback(): Promise<{ routed: number; skipped: number; errors: number }> {
  if (!supabase) return { routed: 0, skipped: 0, errors: 0 }
  const { data: feedbacks } = await supabase
    .from('tester_feedback')
    .select('*')
    .in('severity', ['blocker', 'high'])
    .eq('status', 'open')
    .limit(50)

  if (!Array.isArray(feedbacks)) return { routed: 0, skipped: 0, errors: 0 }

  let routed = 0, skipped = 0, errors = 0

  for (const fb of feedbacks) {
    if (fb.ray_review_item_id) { skipped++; continue }
    const result = await routeFeedbackToRayReview(fb, supabase)
    if (result.ok) routed++
    else errors++
  }

  return { routed, skipped, errors }
}
