import { requireAdmin } from './_admin-auth.mjs'
import { canonicalApprovalId, companyCycleId, readLiveControlPlane, supabaseRequest } from './_supabase-control-plane.mjs'

// Canonical remote receipt: RAY_DECISION_RECORDED -> runtime consumer.

const json = (statusCode, body) => ({ statusCode, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' }, body: JSON.stringify(body) })

export async function handler(event) {
  const auth = await requireAdmin(event)
  if (!auth.ok) return json(auth.statusCode, { error: auth.error })
  if (event.httpMethod !== 'POST') return json(405, { error: 'method_not_allowed' })
  let body
  try { body = JSON.parse(event.body || '{}') } catch { return json(400, { error: 'invalid_json' }) }
  const { approval_id: approvalId, decision, feedback = '', idempotency_key: suppliedKey } = body
  if (!approvalId || !['approve', 'reject', 'request_changes'].includes(decision)) return json(400, { error: 'approval_id_and_supported_decision_required' })
  const controlPlane = await readLiveControlPlane()
  const current = controlPlane.approvals.find(row => canonicalApprovalId(row) === approvalId)
  if (!current) return json(404, { error: 'approval_not_found', approval_id: approvalId })
  if (current.status !== 'pending') return json(409, { error: 'approval_not_pending', status: current.status })
  const status = decision === 'approve' ? 'approved' : decision === 'reject' ? 'rejected' : 'revise'
  const idempotencyKey = suppliedKey || `ray-decision:${approvalId}:${status}`
  const cycleId = companyCycleId(current)
  const decidedAt = new Date().toISOString()
  const payload = { ...(current.payload || {}), decision, feedback, canonical_approval_id: approvalId, company_cycle_id: cycleId, idempotency_key: idempotencyKey }
  const updated = await supabaseRequest(`approvals?id=eq.${encodeURIComponent(current.id)}`, { method: 'PATCH', body: { status, payload, approved_by: auth.userId, decided_at: decidedAt } })
  const eventRows = await supabaseRequest('nexus_events', { method: 'POST', body: { lane: 'system', source: 'admin', action: 'ray_decision_recorded', status: 'success', title: `Ray ${status} approval`, summary: feedback || `Ray recorded ${status}.`, payload: { approval_id: approvalId, remote_approval_id: current.id, company_cycle_id: cycleId, decision: status, feedback, idempotency_key: idempotencyKey }, correlation_id: cycleId, approval_id: current.id } })
  const receipt = { receipt_id: `supabase_decision_${current.id}_${status}`, approval_id: approvalId, remote_approval_id: current.id, decision: status, company_cycle_id: cycleId, recorded_at: decidedAt, durable: true, idempotency_key: idempotencyKey }
  return json(200, { ok: true, receipt, approval: Array.isArray(updated) ? updated[0] : updated, event: Array.isArray(eventRows) ? eventRows[0] : eventRows, resumed: status === 'approved', resume: 'canonical_runtime_decision_consumer' })
}
