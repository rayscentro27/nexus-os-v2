import fs from 'node:fs'
import path from 'node:path'
import { requireAdmin } from './_admin-auth.mjs'

const json = (statusCode, body) => ({ statusCode, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' }, body: JSON.stringify(body) })
const root = process.cwd()
const now = () => new Date().toISOString()
const lines = file => { try { return fs.readFileSync(file, 'utf8').split('\n').filter(Boolean).map(line => JSON.parse(line)) } catch { return [] } }
const append = (file, row) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.appendFileSync(file, JSON.stringify(row) + '\n') }

export async function handler(event) {
  const auth = await requireAdmin(event)
  if (!auth.ok) return json(auth.statusCode, { error: auth.error })
  if (event.httpMethod !== 'POST') return json(405, { error: 'method_not_allowed' })
  let body
  try { body = JSON.parse(event.body || '{}') } catch { return json(400, { error: 'invalid_json' }) }
  const { approval_id: approvalId, decision, feedback = '' } = body
  if (!approvalId || !['approve', 'reject', 'request_changes'].includes(decision)) return json(400, { error: 'approval_id_and_supported_decision_required' })
  const approvalPath = path.join(root, 'data/governed/approvals.jsonl')
  const current = [...lines(approvalPath)].reverse().find(row => row.id === approvalId)
  if (!current) return json(404, { error: 'approval_not_found', approval_id: approvalId })
  if (current.status !== 'pending') return json(409, { error: 'approval_not_pending', status: current.status })
  const status = decision === 'approve' ? 'approved' : decision === 'reject' ? 'rejected' : 'revise'
  const updated = { ...current, status, resolution: feedback || status, resolved_at: now(), resolved_by: auth.email || 'ray' }
  append(approvalPath, updated)
  const cycleId = current.input_summary?.company_cycle_id
  if (cycleId) {
    const cyclePath = path.join(root, `data/runtime/company_cycles/${cycleId}.json`)
    try {
      const state = JSON.parse(fs.readFileSync(cyclePath, 'utf8'))
      state.campaign_approval_status = status === 'approved' ? 'APPROVED' : status === 'revise' ? 'REQUEST_CHANGES' : 'REJECTED'
      state.current_stage = status === 'approved' ? 'SOCIAL' : status === 'revise' ? 'DEPARTMENTS' : 'ADMIN_APPROVAL'
      state.status = status === 'approved' ? 'WAITING_EXTERNAL' : status === 'revise' ? 'ACTIVE' : 'REJECTED'
      state.stages = state.stages || {}
      state.stages.ADMIN_APPROVAL = { ...(state.stages.ADMIN_APPROVAL || {}), status: status === 'approved' ? 'PASS_REAL' : status === 'revise' ? 'REQUEST_CHANGES' : 'REJECTED', latest_result: feedback || status, next_action: status === 'approved' ? 'Continue to Social and Email receipt validation.' : status === 'revise' ? 'Route revision feedback to the assigned department.' : 'Cycle closed unless Ray reopens it.' }
      if (status === 'approved') state.stages.SOCIAL = { status: 'BLOCKED_EXTERNAL', owner: 'social_distribution', latest_result: 'No authenticated configured GoClear posting account is present.', next_action: 'Connect or select an approved account.' }
      fs.writeFileSync(cyclePath, JSON.stringify(state, null, 2) + '\n')
      append(path.join(root, 'data/governed/company_cycles.jsonl'), { schema_version: 'nexus.company-cycle.v1', company_cycle_id: cycleId, event: 'RAY_DECISION_RECORDED', approval_id: approvalId, decision: status, feedback, recorded_at: now(), resumed_stage: state.current_stage })
    } catch (error) { return json(500, { error: 'cycle_resume_projection_failed', detail: String(error).slice(0, 200) }) }
  }
  const receipt = { receipt_id: `decision_${Date.now().toString(36)}`, approval_id: approvalId, decision: status, company_cycle_id: cycleId || null, recorded_at: now(), durable: true }
  append(path.join(root, 'data/governed/audit.jsonl'), { event_id: receipt.receipt_id, type: 'ray_decision_recorded', ...receipt })
  return json(200, { ok: true, receipt, approval: updated, resumed: status === 'approved' })
}
