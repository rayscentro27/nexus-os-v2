import { supabase } from './supabaseClient'

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

function sanitize(text: string | null, maxLen = 2000): string {
  if (!text) return ''
  return text.replace(/[<>]/g, '').slice(0, maxLen)
}

export async function routeFeedbackToRayReview(feedback: FeedbackRow): Promise<{ ok: boolean; rayReviewId?: string; error?: string }> {
  if (!supabase) return { ok: false, error: 'Supabase not configured' }
  if (feedback.severity !== 'blocker' && feedback.severity !== 'high') {
    return { ok: false, error: 'Only blocker/high feedback is routed to Ray Review' }
  }

  if (feedback.ray_review_item_id) {
    return { ok: true, rayReviewId: feedback.ray_review_item_id }
  }

  const { data: payloadRows } = await Promise.resolve(
    supabase
      .from('task_requests')
      .select('id, payload')
      .eq('task_type', 'ray_review_item')
      .limit(200)
  ).catch(() => ({ data: null }))

  if (Array.isArray(payloadRows)) {
    const duplicate = payloadRows.find((row: any) => {
      const p = typeof row.payload === 'string' ? JSON.parse(row.payload) : row.payload
      return p?.feedback_record_id === feedback.id
    })
    if (duplicate) {
      await supabase
        .from('tester_feedback')
        .update({ ray_review_item_id: duplicate.id, status: 'in_review', updated_at: new Date().toISOString() })
        .eq('id', feedback.id)
      return { ok: true, rayReviewId: duplicate.id }
    }
  }

  const commit = feedback.build_commit || import.meta.env?.VITE_BUILD_COMMIT || 'unknown'

  const payload = {
    title: `[${feedback.severity.toUpperCase()}] Persona ${feedback.persona.toUpperCase()}: ${feedback.issue_title}`,
    category: 'tester_feedback',
    riskLevel: SEVERITY_TO_RISK[feedback.severity] || 'medium',
    externalAction: false,
    recommendation: `Tester-reported ${feedback.severity} issue requiring Ray review.`,
    source: `tester_feedback:${feedback.id}`,
    data_source: 'tester_feedback',
    synthetic: true,
    feedback_record_id: feedback.id,
    persona: feedback.persona,
    page_route: feedback.page_route,
    workflow_step: feedback.workflow_step,
    issue_title: feedback.issue_title,
    issue_description: sanitize(feedback.issue_description),
    expected_behavior: sanitize(feedback.expected_behavior),
    actual_behavior: sanitize(feedback.actual_behavior),
    severity: feedback.severity,
    reproducibility: feedback.reproducibility,
    browser_device: feedback.browser_device,
    fixture_version: feedback.fixture_version,
    build_commit: commit,
    evidence_reference: feedback.evidence_reference,
    proposed_owner: 'ray',
    proposed_next_action: 'Review the reported issue and decide on resolution.',
    status_required: 'pending',
  }

  const { data: inserted, error: insertError } = await supabase
    .from('task_requests')
    .insert({
      task_type: 'ray_review_item',
      requested_by: 'tester_feedback',
      sensitivity: feedback.severity === 'blocker' ? 'internal_summary' : 'public',
      status: 'requested',
      payload,
    })
    .select('id')
    .single()

  if (insertError || !inserted) {
    return { ok: false, error: `Failed to create Ray Review item: ${insertError?.message || 'unknown'}` }
  }

  await supabase
    .from('tester_feedback')
    .update({
      ray_review_item_id: inserted.id,
      status: 'in_review',
      updated_at: new Date().toISOString(),
    })
    .eq('id', feedback.id)

  return { ok: true, rayReviewId: inserted.id }
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
    const result = await routeFeedbackToRayReview(fb)
    if (result.ok) routed++
    else errors++
  }

  return { routed, skipped, errors }
}
