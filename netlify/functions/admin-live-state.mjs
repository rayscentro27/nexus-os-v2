import fs from 'node:fs'
import path from 'node:path'

const json = (statusCode, body) => ({ statusCode, headers: { 'content-type': 'application/json', 'cache-control': 'no-store' }, body: JSON.stringify(body) })
const env = (key) => process.env[key] || ''
const root = process.cwd()
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'src/data/adminCompanyState.json'), 'utf8'))

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
  const latest = new Map(); for (const row of [...followups].reverse()) if (row.claim_id && !latest.has(row.claim_id)) latest.set(row.claim_id, row)
  const cutoff = now - 24 * 60 * 60 * 1000
  const executions24h = executions.filter(row => Date.parse(row.completed_at || row.started_at || '') >= cutoff)
  const queue = Array.isArray(workOrders) ? workOrders : []
  const states = Object.fromEntries(['READY', 'CLAIMED', 'RUNNING', 'COMPLETED', 'FAILED_RETRYABLE', 'WAITING_APPROVAL', 'BLOCKED', 'SUPERSEDED'].map(state => [state, queue.filter(row => String(row.status || '').toUpperCase() === state).length]))
  const supervisorLast = supervisorHeartbeat?.generated_at || supervisor?.generated_at || null
  const currentLane = research?.selected_lane_name || research?.selected_lane_id || snapshot.research.current_lane
  const goals = readJson('data/runtime/company_goal_portfolio.json')
  return {
    ...snapshot,
    generated_at: new Date().toISOString(),
    data_age_seconds: ageSeconds(supervisorLast, now),
    freshness_seconds: ageSeconds(supervisorLast, now),
    provenance: 'authenticated server-side projection of canonical runtime state',
    system_health: supervisorHeartbeat?.status === 'ACTIVE' ? 'HEALTHY' : 'DEGRADED',
    research: { ...snapshot.research, health: research?.heartbeat === 'ACTIVE' ? 'ACTIVE' : 'DEGRADED', process_health: research?.worker_state || 'UNKNOWN', productivity_health: research?.result_status || 'UNKNOWN', current_lane: currentLane, next_lane: research?.next_action || snapshot.research.next_lane, last_real_run: research?.last_real_output || snapshot.research.last_real_run, next_research_action: research?.next_action || 'Inspect research queue' },
    youtube: { ...snapshot.youtube, status: youtubeQueue?.status || 'UNKNOWN', videos_processed_24h: 0, follow_ups_pending: [...latest.values()].filter(row => ['UNVERIFIED', 'PARTIALLY_SUPPORTED', 'FAILED_RETRYABLE', null].includes(row.status)).length, follow_ups_executed_24h: executions24h.length, validated_claims_24h: executions24h.filter(row => row.revalidation_result === 'VALIDATED').length },
    departments: { ...snapshot.departments, consumer_status: department ? 'ACTIVE' : 'UNKNOWN', executable_queue_depth: states.READY + states.CLAIMED + states.RUNNING + states.FAILED_RETRYABLE, running_work: states.RUNNING, completions_24h: states.COMPLETED },
    notifications: { status: 'launchd-scheduled', latest: null, morning_digest: 'scheduler-managed' },
    runtime: { supervisor_status: supervisor?.supervisor_status || 'UNKNOWN', supervisor_last_heartbeat: supervisorLast, active_operator: 'launchd-supervised', scheduler: research?.scheduler || 'UNKNOWN', next_wake: research?.next_wake || snapshot.next_wake_at, next_machine_action: research?.next_action || snapshot.next_machine_action },
    queue_metrics: { total_historical_records: queue.length, executable_queue_depth: states.READY + states.CLAIMED + states.RUNNING + states.FAILED_RETRYABLE, ...states },
    active_goals: { count: Array.isArray(goals) ? goals.length : (Array.isArray(goals?.goals) ? goals.goals.length : null), source: 'canonical runtime aggregate' },
    human_gated_work: states.WAITING_APPROVAL,
    blocked_work: states.BLOCKED,
    ray_decision_count: snapshot.ray_decisions?.count || 0,
  }
}

export async function handler(event) {
  try {
    const authorization = event.headers?.authorization || event.headers?.Authorization
    if (!authorization?.startsWith('Bearer ')) return json(401, { error: 'admin_authentication_required' })
    const url = (env('VITE_SUPABASE_URL') || env('SUPABASE_URL')).replace(/\/$/, '')
    const anon = env('VITE_SUPABASE_ANON_KEY') || env('SUPABASE_ANON_KEY')
    if (!url || !anon) return json(503, { error: 'admin_read_model_unavailable' })
    const userResponse = await fetch(`${url}/auth/v1/user`, { headers: { apikey: anon, authorization } })
    const user = await userResponse.json().catch(() => null)
    if (!userResponse.ok || !user?.id) return json(401, { error: 'authenticated_nexus_session_required' })
    const headers = { apikey: anon, authorization, 'content-type': 'application/json' }
    const adminResponse = await fetch(`${url}/rest/v1/admin_users?id=eq.${encodeURIComponent(user.id)}&active=neq.false&select=role&limit=1`, { headers })
    const admins = await adminResponse.json().catch(() => [])
    let role = Array.isArray(admins) && admins[0]?.role
    if (!role) {
      const membershipResponse = await fetch(`${url}/rest/v1/tenant_memberships?user_id=eq.${encodeURIComponent(user.id)}&role=in.(super_admin,admin,operator)&select=role&limit=1`, { headers })
      const memberships = await membershipResponse.json().catch(() => [])
      role = Array.isArray(memberships) && memberships[0]?.role
    }
    if (!role) return json(403, { error: 'admin_access_required' })
    return json(200, {
      ...liveProjection(),
      read_model: 'authenticated_admin_live_runtime_projection',
      authorization: { allowed: true, role: String(role) },
      sensitive_fields_excluded: true,
    })
  } catch {
    return json(500, { error: 'admin_read_model_failed' })
  }
}
