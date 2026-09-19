import fs from 'node:fs'
import path from 'node:path'
import { requireAdmin } from './_admin-auth.mjs'

const json = (statusCode, body) => ({ statusCode, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' }, body: JSON.stringify(body) })
const env = (key) => process.env[key] || ''
const root = process.cwd()
const fallbackSnapshot = { generated_at: null, system_health: 'DEGRADED', research: {}, youtube: {}, departments: {}, campaigns: {}, opportunities: {}, handoffs: {}, next_machine_action: 'Continue canonical runtime', ray_decisions: { count: 0, items: [] }, campaign_list: [], recent_findings: [] }
const snapshot = (() => { try { return JSON.parse(fs.readFileSync(path.join(root, 'src/data/adminCompanyState.json'), 'utf8')) } catch { return fallbackSnapshot } })()

const readJson = (relative) => { try { return JSON.parse(fs.readFileSync(path.join(root, relative), 'utf8')) } catch { return null } }
const readJsonl = (relative) => { try { return fs.readFileSync(path.join(root, relative), 'utf8').split('\n').filter(Boolean).map(line => JSON.parse(line)) } catch { return [] } }
const ageSeconds = (value, now) => { const time = value ? Date.parse(value) : NaN; return Number.isFinite(time) ? Math.max(0, Math.round((now - time) / 1000)) : null }

export function liveProjection() {
  const now = Date.now()
  const supervisor = readJson('data/runtime/nexus_supervisor_state.json')
  const supervisorHeartbeat = readJson('reports/runtime/nexus_supervisor_heartbeat.json')
  const research = readJson('data/runtime/research_heartbeat.json')
  const department = readJson('reports/runtime/department_work_consumer_heartbeat.json')
  const followups = readJsonl('data/governed/youtube_follow_ups.jsonl')
  const executions = readJsonl('data/governed/youtube_follow_up_executions.jsonl')
  const youtubeQueue = readJson('data/runtime/youtube_backfill_queue.json')
  const workOrders = readJson('data/runtime/active_operator_work_orders.json')
  const researchV2Sources = readJsonl('data/governed/research_v2_sources.jsonl')
  const researchV2Questions = readJsonl('data/governed/research_v2_questions.jsonl')
  const researchV2FollowUps = readJsonl('data/governed/research_v2_follow_ups.jsonl')
  const researchV2Strategies = readJsonl('data/governed/research_v2_strategies.jsonl')
  const researchV2Reviews = readJsonl('data/governed/research_v2_review_queue.jsonl')
  const governedApprovals = readJsonl('data/governed/approvals.jsonl')
  const cycleState = readJson('data/runtime/company_cycles/company_cycle_ddc1b360d7a64a3085b819bec48554f1.json')
  const latest = new Map(); for (const row of [...followups].reverse()) if (row.claim_id && !latest.has(row.claim_id)) latest.set(row.claim_id, row)
  const cutoff = now - 24 * 60 * 60 * 1000
  const executions24h = executions.filter(row => Date.parse(row.completed_at || row.started_at || '') >= cutoff)
  const queue = Array.isArray(workOrders) ? workOrders : []
  const states = Object.fromEntries(['READY', 'CLAIMED', 'RUNNING', 'COMPLETED', 'FAILED_RETRYABLE', 'WAITING_APPROVAL', 'BLOCKED', 'SUPERSEDED'].map(state => [state, queue.filter(row => String(row.status || '').toUpperCase() === state).length]))
  const supervisorLast = supervisorHeartbeat?.generated_at || supervisor?.generated_at || null
  const currentLane = research?.selected_lane_name || research?.selected_lane_id || snapshot.research.current_lane
  const goals = readJson('data/runtime/company_goal_portfolio.json')
  const latestReviews = new Map(); for (const row of [...researchV2Reviews].reverse()) if (row.review_item_id && !latestReviews.has(row.review_item_id)) latestReviews.set(row.review_item_id, row)
  const reviewItems = [...latestReviews.values()].filter(row => row.status === 'DRAFT_REVIEW_REQUIRED')
  const latestApprovals = new Map(); for (const row of [...governedApprovals].reverse()) if (row.id && !latestApprovals.has(row.id)) latestApprovals.set(row.id, row)
  const approvalItems = [...latestApprovals.values()].filter(row => row.status === 'pending').map(row => ({
    review_item_id: row.id, approval_id: row.id, company_cycle_id: row.input_summary?.company_cycle_id || cycleState?.company_cycle_id || null,
    type: row.action_id === 'client.sends' ? 'CAMPAIGN_APPROVAL' : 'GOVERNED_APPROVAL',
    title: row.action_summary || 'Governed approval', status: 'DRAFT_REVIEW_REQUIRED',
    why_human_review_required: row.action_summary || 'Ray approval is required before external action.',
    what_ray_is_deciding: 'Approve, reject, or request changes to the bounded action.',
    options: ['approve', 'reject', 'request_changes', 'ask_nova'], risk: row.risk_level || 'high',
    scope: row.input_summary || {}, external_action_if_approved: 'Resume the existing company cycle; publication and delivery remain separately receipt-gated.',
    artifact_refs: row.evidence_refs || [], source_object: row.action_id, created_at: row.created_at,
  }))
  const openQuestions = researchV2Questions.filter(row => row.status === 'OPEN').length
  const researchV2 = {
    sources: researchV2Sources.length,
    open_questions: openQuestions,
    follow_ups: researchV2FollowUps.length,
    strategy_theses: researchV2Strategies.length,
    human_review_queue_count: reviewItems.length,
    productive_research: Boolean(researchV2Sources.length || researchV2FollowUps.length),
    machine_work_remains: Boolean(openQuestions || researchV2FollowUps.length || researchV2Sources.length),
    global_stop_required: false,
  }
  return {
    ...snapshot,
    generated_at: new Date().toISOString(),
    data_age_seconds: ageSeconds(supervisorLast, now),
    freshness_seconds: ageSeconds(supervisorLast, now),
    provenance: 'authenticated server-side projection of canonical runtime state',
    system_health: supervisorHeartbeat?.status === 'ACTIVE' ? 'HEALTHY' : 'DEGRADED',
    research: { ...snapshot.research, health: research?.heartbeat === 'ACTIVE' ? 'ACTIVE' : 'DEGRADED', process_health: research?.worker_state || 'UNKNOWN', productivity_health: research?.result_status || 'UNKNOWN', current_lane: currentLane, next_lane: research?.next_action || snapshot.research.next_lane, last_real_run: research?.last_real_output || snapshot.research.last_real_run, next_research_action: research?.next_action || 'Inspect research queue' },
    research_v2: researchV2,
    youtube: { ...snapshot.youtube, status: youtubeQueue?.status || 'UNKNOWN', videos_processed_24h: 0, follow_ups_pending: [...latest.values()].filter(row => ['UNVERIFIED', 'PARTIALLY_SUPPORTED', 'FAILED_RETRYABLE', null].includes(row.status)).length, follow_ups_executed_24h: executions24h.length, validated_claims_24h: executions24h.filter(row => row.revalidation_result === 'VALIDATED').length },
    departments: { ...snapshot.departments, consumer_status: department ? 'ACTIVE' : 'UNKNOWN', executable_queue_depth: states.READY + states.CLAIMED + states.RUNNING + states.FAILED_RETRYABLE, running_work: states.RUNNING, completions_24h: states.COMPLETED },
    notifications: { status: 'launchd-scheduled', latest: null, morning_digest: 'scheduler-managed' },
    runtime: { supervisor_status: supervisor?.supervisor_status || 'UNKNOWN', supervisor_last_heartbeat: supervisorLast, active_operator: 'launchd-supervised', scheduler: research?.scheduler || 'UNKNOWN', next_wake: research?.next_wake || snapshot.next_wake_at, next_machine_action: research?.next_action || snapshot.next_machine_action },
    queue_metrics: { total_historical_records: queue.length, executable_queue_depth: states.READY + states.CLAIMED + states.RUNNING + states.FAILED_RETRYABLE, ...states },
    active_goals: { count: Array.isArray(goals) ? goals.length : (Array.isArray(goals?.goals) ? goals.goals.length : null), source: 'canonical runtime aggregate' },
    human_gated_work: states.WAITING_APPROVAL,
    blocked_work: states.BLOCKED,
    ray_decisions: { ...(snapshot.ray_decisions || {}), count: reviewItems.length + approvalItems.length, items: [...approvalItems, ...reviewItems] },
    ray_decision_count: reviewItems.length + approvalItems.length,
    company_cycle: cycleState || null,
    review_data_source: 'GOVERNED_LIVE_READ_MODEL',
  }
}

export async function handler(event) {
  try {
    const auth = await requireAdmin(event)
    if (!auth.ok) return json(auth.statusCode, { error: auth.error })
    return json(200, {
      ...liveProjection(),
      read_model: 'authenticated_admin_live_runtime_projection',
      authorization: { allowed: true, role: auth.role },
      sensitive_fields_excluded: true,
    })
  } catch {
    return json(500, { error: 'admin_read_model_failed' })
  }
}
