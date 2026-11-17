import repoRegistry from '../../data/repoIntelligenceRegistry';
import { getConnectorRegistry, connectorSafetyInvariants } from '../../hermes/nexus/nexusConnectorRegistry';
import { listTableDetailed, type TableQueryResult } from '../../services/db';
import { getBrainProfiles } from '../brains/brainRegistry';
import { buildCapabilityOSSummary } from '../capabilities/capabilityRegistry';
import { buildKnowledgeHealthSummary } from '../intelligence/knowledgeHealth';
import type {
  DepartmentStatus,
  ExecutiveActionItem,
  ExecutiveApprovalItem,
  ExecutiveBrief,
  ExecutiveCommandCenterState,
  ExecutiveEvidence,
  ExecutiveHealthItem,
  ExecutiveMetric,
  GovernedWorkItem,
  CompanyHandoff,
  ResearchObservability,
  RepoIntelligenceItem,
} from './executiveTypes';

type Row = Record<string, unknown>;

const nowIso = () => new Date().toISOString();

export function phoenixDateTime(now: Date = new Date()): string {
  try {
    return new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/Phoenix',
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: 'short',
    }).format(now);
  } catch {
    return now.toISOString();
  }
}

export const evidence = (
  state: ExecutiveEvidence['state'],
  source: string,
  confidence: ExecutiveEvidence['confidence'] = 'MEDIUM',
): ExecutiveEvidence => ({
  state,
  source,
  observedAt: nowIso(),
  freshness: state === 'LIVE' || state === 'CACHED' ? 'CURRENT' : state === 'REPORT_BACKED' ? 'STALE' : 'UNKNOWN',
  confidence,
});

function sourceFromResult(result: TableQueryResult<Row>, table: string): ExecutiveEvidence {
  if (result.status === 'connected_with_records' || result.status === 'no_records') {
    return evidence('LIVE', `Supabase ${table} (${result.status})`, 'HIGH');
  }
  if (result.status === 'no_authenticated_session') return evidence('BLOCKED', `Supabase ${table}: no authenticated admin session`, 'HIGH');
  if (result.status === 'missing_env') return evidence('BLOCKED', `Supabase ${table}: environment not configured`, 'HIGH');
  if (result.status === 'rls_denied_no_access') return evidence('BLOCKED', `Supabase ${table}: RLS denied`, 'HIGH');
  return evidence('UNKNOWN', `Supabase ${table}: ${result.status}`, 'MEDIUM');
}

export function normalizeApprovalState(status: unknown): ExecutiveApprovalItem['state'] {
  const value = String(status ?? '').toLowerCase();
  if (['approved', 'done'].includes(value)) return 'APPROVED';
  if (['rejected', 'declined'].includes(value)) return 'REJECTED';
  if (['revise', 'revision_requested', 'needs_revision'].includes(value)) return 'REVISION_REQUESTED';
  if (['held', 'deferred'].includes(value)) return 'DEFERRED';
  if (['expired'].includes(value)) return 'EXPIRED';
  if (['blocked', 'failed'].includes(value)) return 'BLOCKED';
  return 'PENDING';
}

export function normalizeWorkLifecycle(taskStatus: unknown, approvalState?: ExecutiveApprovalItem['state'] | 'NOT_REQUIRED', jobStatus?: unknown): GovernedWorkItem['lifecycle'] {
  const task = String(taskStatus ?? '').toLowerCase();
  const job = String(jobStatus ?? '').toLowerCase();
  if (['cancelled', 'canceled'].includes(task) || ['cancelled', 'canceled'].includes(job)) return 'CANCELLED';
  if (['failed', 'error'].includes(task) || ['failed', 'error'].includes(job)) return 'FAILED';
  if (['blocked'].includes(task) || ['blocked'].includes(job) || approvalState === 'BLOCKED') return 'BLOCKED';
  if (['running', 'in_progress', 'processing'].includes(task) || ['running', 'in_progress', 'processing'].includes(job)) return 'RUNNING';
  if (['done', 'completed', 'success'].includes(task) || ['done', 'completed', 'success'].includes(job)) return 'COMPLETED';
  if (approvalState === 'PENDING') return 'AWAITING_APPROVAL';
  if (approvalState === 'APPROVED') return job ? 'QUEUED' : 'APPROVED';
  if (approvalState === 'REVISION_REQUESTED') return 'NEEDS_REVIEW';
  if (approvalState === 'DEFERRED') return 'DEFERRED';
  if (['draft'].includes(task)) return 'DRAFT';
  if (['requested', 'assigned', 'queued', 'stubbed'].includes(task) || ['queued', 'stubbed'].includes(job)) return 'QUEUED';
  return 'NEEDS_REVIEW';
}

function text(value: unknown, fallback: string): string {
  if (typeof value === 'string' && value.trim()) return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return fallback;
}

function payload(row: Row): Row {
  return row.payload && typeof row.payload === 'object' ? row.payload as Row : {};
}

export function normalizeApprovalRows(rows: Row[], source: ExecutiveEvidence): ExecutiveApprovalItem[] {
  return rows.map((row, index) => {
    const p = payload(row);
    return {
      id: text(row.id, `approval-${index}`),
      type: text(row.item_type ?? row.task_type ?? p.type, 'approval'),
      source: text(row.source ?? p.source, 'approvals/task_requests'),
      proposer: text(row.requested_by ?? p.proposer, 'Hermes or Nexus operator'),
      department: text(row.lane ?? p.department ?? p.category, 'executive'),
      riskLevel: String(row.risk_level ?? row.sensitivity ?? p.riskLevel ?? 'UNKNOWN').toUpperCase() as ExecutiveApprovalItem['riskLevel'],
      summary: text(row.summary ?? row.title ?? p.summary ?? p.recommendation, 'Review required before any action runs.'),
      evidence: source,
      financialEffect: text(p.financialEffect, 'Unknown or not applicable'),
      customerEffect: text(p.customerEffect, 'Unknown or not applicable'),
      privacyEffect: text(p.privacyEffect, 'Unknown or not applicable'),
      deadline: text(row.deadline ?? p.deadline, 'No deadline recorded'),
      state: normalizeApprovalState(row.status),
      requiredApprover: 'Ray Davis',
      linkedTaskRequest: text(row.task_request_id ?? p.taskRequestId, '') || null,
      linkedAgentJob: text(row.job_id ?? p.jobId, '') || null,
      linkedEventHistory: Array.isArray(p.events) ? p.events.map(String) : [],
    };
  });
}

export function normalizeGovernedWorkRows(taskRows: Row[], approvalRows: Row[], jobRows: Row[], source: ExecutiveEvidence): GovernedWorkItem[] {
  const approvalsByTask = new Map(approvalRows.map((row) => [text(row.task_request_id ?? payload(row).taskRequestId, ''), normalizeApprovalState(row.status)]));
  return taskRows.map((row, index) => {
    const p = payload(row);
    const id = text(row.id, `task-${index}`);
    const matchingJob = jobRows.find((job) => text(job.task_request_id ?? payload(job).taskRequestId, '') === id);
    const recordedApproval = p.approvalStatus ?? row.approval_status;
    const approvalState = approvalsByTask.get(id) ?? (recordedApproval ? normalizeApprovalState(recordedApproval) : 'NOT_REQUIRED');
    const lifecycle = normalizeWorkLifecycle(row.status, approvalState, matchingJob?.status);
    return {
      id,
      goalId: text(p.goal_id ?? row.goal_id, 'NOT_CONNECTED'),
      parentGoalId: text(p.parent_goal_id ?? row.parent_goal_id, 'NOT_CONNECTED'),
      title: text(row.title ?? p.title ?? p.action ?? row.task_type, 'Governed work item'),
      department: text(row.department ?? p.department ?? row.task_type, 'operations'),
      assignee: text(row.assigned_worker_type ?? matchingJob?.worker ?? p.assignee, 'Unassigned'),
      lifecycle,
      approvalState,
      executionStatus: text(matchingJob?.status ?? row.status, 'not queued'),
      blocker: lifecycle === 'BLOCKED' || lifecycle === 'FAILED' ? text(row.result_summary ?? p.blocker, 'Review failure evidence') : '',
      nextAction: lifecycle === 'AWAITING_APPROVAL' ? 'Ray approval required' : text(p.action ?? p.next_action, lifecycle === 'COMPLETED' ? 'Review proof event' : 'Derive from durable work state'),
      evidence: source,
      createdAt: text(row.created_at, '') || null,
      updatedAt: text(row.updated_at, '') || null,
      evidenceRequest: Array.isArray(p.missing_evidence) ? (p.missing_evidence as unknown[]).map(String).join('; ')
        : text(p.evidence_request ?? p.reason, 'UNAVAILABLE'),
    };
  });
}

function departmentMatches(departmentId: string, value: string): boolean {
  const text = value.toLowerCase().replace(/[^a-z0-9]+/g, ' ');
  const id = departmentId.toLowerCase();
  const aliases: Record<string, string[]> = {
    research: ['research', 'alpha'], opportunities: ['opportunit', 'revenue'], finance: ['finance', 'ledger'], trading: ['trading'],
    marketing: ['marketing', 'growth'], creative: ['creative', 'content'], labs: ['labs', 'lab'],
    upgrade: ['upgrade', 'governance'], systems: ['systems', 'engineering', 'operations'],
  };
  const key = Object.keys(aliases).find((candidate) => id.includes(candidate)) || id;
  return (aliases[key] || [key.replace(/_/g, ' ')]).some((alias) => text.includes(alias));
}

function normalizeCompanyHandoffs(rows: Row[]): CompanyHandoff[] {
  return rows.map((row, index) => {
    const p = payload(row);
    const acknowledgement = p.acknowledgement && typeof p.acknowledgement === 'object' ? p.acknowledgement as Row : {};
    const continuation = p.continuation && typeof p.continuation === 'object' ? p.continuation as Row : {};
    const result = p.result && typeof p.result === 'object' ? p.result as Row : {};
    const rejection = result.rejection && typeof result.rejection === 'object' ? result.rejection as Row : null;
    return {
      handoffId: text(row.handoff_id ?? row.id, `handoff-${index}`),
      sourceDepartment: text(row.source_department, 'Unknown'),
      targetDepartment: text(row.target_department, 'Unknown'),
      subject: text(row.topic, 'Unspecified work'),
      status: text(row.status, 'UNKNOWN'),
      createdAt: text(row.created_at, '') || null,
      acknowledgedAt: text(row.acknowledged_at ?? acknowledgement.at, '') || null,
      currentOwner: text(continuation.owner_department ?? row.current_owner ?? p.current_owner ?? acknowledgement.by, 'Unassigned'),
      currentGoal: text(continuation.receiver_goal_id ?? row.parent_goal_id ?? p.goal_id ?? p.parent_goal_id, 'Not attached'),
      currentAction: text(continuation.next_action ?? row.requested_action ?? row.next_action ?? p.next_action, 'Not recorded'),
      outcome: text(result.status ?? row.processing_result_ref ?? row.last_error ?? p.outcome, 'No outcome recorded'),
      workOrderId: text(row.receiving_work_order_id ?? continuation.work_order_id, ''),
      currentStage: text(continuation.current_stage ?? row.status, 'Not recorded'),
      rejection: rejection ? {
        reason: text(rejection.reason, 'Not recorded'),
        evidence: Array.isArray(rejection.evidence) ? rejection.evidence : [],
        failedCriteria: Array.isArray(rejection.failed_criteria) ? rejection.failed_criteria : [],
        whatWasTested: text(rejection.what_was_tested, 'Not recorded'),
        whatWasObserved: rejection.what_was_observed ?? 'Not recorded',
        whatWouldChangeTheDecision: text(rejection.what_would_change_the_decision, 'Not recorded'),
        nextAction: text(rejection.next_action, 'Not recorded'),
        nextActionOwner: text(rejection.next_action_owner, 'Not recorded'),
        parentGoalStatus: text(rejection.parent_goal_status, 'NOT_RECORDED'),
      } : null,
    };
  });
}

function buildResearchObservability(sources: Row[], memory: Row[], questions: Row[], findings: Row[], notebooks: Row[], handoffRows: Row[], statuses: Record<string, string>, followupRows: Row[] = []): ResearchObservability {
  const memoryRecords = memory.map((row) => ({ ...((row.payload && typeof row.payload === 'object') ? row.payload as Row : {}), ...row }));
  const cutoff = Date.now() - 24 * 60 * 60 * 1000;
  const recent = (row: Row, fields: string[]) => {
    const value = fields.map((field) => row[field]).find(Boolean);
    const stamp = value ? Date.parse(String(value)) : Number.NaN;
    return Number.isFinite(stamp) && stamp >= cutoff;
  };
  const metadata = (row: Row): Row => row.metadata && typeof row.metadata === 'object' ? row.metadata as Row : {};
  const durableSources = sources.filter((row) => ['DESIGNATED_YOUTUBE_CHANNEL', 'DESIGNATED_SOURCE', 'DISCOVERY_PROVIDER', 'STRATEGIC_REFERENCE'].includes(String(metadata(row).record_kind || '')));
  const designatedSources = durableSources.filter((row) => ['DESIGNATED_YOUTUBE_CHANNEL', 'DESIGNATED_SOURCE'].includes(String(metadata(row).record_kind || ''))).map((row) => {
    const m = metadata(row);
    return { name: text(m.name ?? row.title, 'Unnamed source'), type: text(m.source_type ?? row.source_type, 'UNKNOWN'),
      category: text(m.category, 'GENERAL'), targetDepartment: text(m.target_department, 'RESEARCH'),
      priority: text(m.priority, 'UNKNOWN'), enabled: String(Boolean(m.enabled)), mode: text(m.monitor_mode, 'DISCOVERY_ONLY') };
  });
  const providers = durableSources.filter((row) => metadata(row).record_kind === 'DISCOVERY_PROVIDER').map((row) => {
    const m = metadata(row);
    return { name: text(m.provider_id ?? row.title, 'Provider'), purpose: text(m.purpose, 'Discovery'),
      enabled: String(Boolean(m.enabled)), liveStatus: text(m.live_status, 'NOT_PROVEN') };
  });
  const recentMemory = memoryRecords.filter((row) => recent(row, ['recorded_at', 'created_at']));
  const queries = recentMemory.filter((row) => row.memory_kind === 'PROACTIVE_QUERY');
  const current = [...queries].sort((a, b) => String(b.recorded_at || '').localeCompare(String(a.recorded_at || '')))[0];
  const caseRows = memoryRecords.filter((row) => row.memory_kind === 'PROACTIVE_RESEARCH_CASE' && String(row.status || '').toUpperCase() !== 'COMPLETED');
  const currentCase = [...caseRows].sort((a, b) => String(b.recorded_at || '').localeCompare(String(a.recorded_at || '')))[0];
  const objectiveIds = new Set(memoryRecords.map((row) => String(row.objective_id || '')).filter(Boolean));
  const openQuestionRows = questions.filter((row) => !['COMPLETED', 'CLOSED', 'CANCELLED'].includes(String(row.status || '').toUpperCase()));
  const currentQuestion = openQuestionRows.find((row) => ['PROCESSING', 'IN_PROGRESS', 'RUNNING'].includes(String(row.status || '').toUpperCase()));
  const resultsByType = sources.filter((row) => metadata(row).record_kind === 'YOUTUBE_MONITOR_TRIAGE_ITEM' && recent(row, ['accessed_at', 'created_at']));
  const recentFindings = findings.filter((row) => recent(row, ['created_at', 'updated_at']));
  const unknown = 'NOT_PROVEN';
  const sourceLive = statuses.sources === 'LIVE';
  const memoryLive = statuses.memory === 'LIVE';
  const questionLive = statuses.questions === 'LIVE';
  const findingLive = statuses.findings === 'LIVE';
  const handoffLive = statuses.handoffs === 'LIVE';
  const notebookLive = statuses.notebooks === 'LIVE';
  const followups = statuses.followups === 'LIVE' ? followupRows.map((row) => {
    const contract = row.contract_payload && typeof row.contract_payload === 'object' ? row.contract_payload as Row : row;
    const qs = Array.isArray(contract.research_questions) ? contract.research_questions as Row[] : [];
    const results = contract.evidence_packet && typeof contract.evidence_packet === 'object'
      ? ((contract.evidence_packet as Row).question_results as Row[] | undefined) ?? [] : [];
    const byId = new Map(results.map((result) => [String(result.question_id ?? ''), String(result.status ?? 'OPEN')]));
    return { requestId: text(contract.research_request_id ?? row.request_id, 'UNAVAILABLE'),
      requestingDepartment: text(contract.requesting_department ?? row.expert_id, 'UNAVAILABLE'),
      subject: text(contract.subject_id ?? row.parent_finding_id, 'UNAVAILABLE'),
      reason: text(contract.reason_more_research_required, 'UNAVAILABLE'),
      questions: qs.map((q) => ({ question: text(q.question, 'UNAVAILABLE'), status: byId.get(String(q.question_id ?? '')) ?? text(q.status, 'OPEN') })),
      currentAction: text(contract.current_action ?? contract.next_action, 'UNAVAILABLE'),
      answersReceived: results.filter((result) => ['ANSWERED', 'PARTIAL'].includes(String(result.status ?? '').toUpperCase())).length,
      remainingGaps: Array.isArray((contract.evidence_packet as Row | undefined)?.remaining_unknowns)
        ? ((contract.evidence_packet as Row).remaining_unknowns as unknown[]).map((gap) => String(gap))
        : Array.isArray(contract.overall_evidence_required) ? contract.overall_evidence_required.map((gap) => String(gap)) : [],
      returnDepartment: text(contract.return_to_department, 'UNAVAILABLE'), returnGoalId: text(contract.return_to_goal_id, 'UNAVAILABLE'),
      decisionUnlocked: text(contract.decision_unlocked_by_answers, 'UNAVAILABLE'), nextAction: text(contract.next_action, 'UNAVAILABLE') };
  }) : statuses.followups === 'NOT_CONNECTED' ? 'NOT_CONNECTED' as const : 'UNAVAILABLE' as const;
  return {
    evidenceStatus: Object.entries(statuses).map(([k, v]) => `${k.toUpperCase()}=${v}`).join(' · '),
    designatedSources: sourceLive ? designatedSources : [],
    providers: sourceLive ? providers : [],
    monitoredItems24h: sourceLive ? resultsByType.length : unknown,
    casesOpen: memoryLive ? caseRows.length : unknown,
    currentlyProcessing: questionLive ? (currentQuestion ? text(currentQuestion.question, 'Research case') : 'No processing case observed') : unknown,
    currentCaseId: memoryLive ? text(currentCase?.case_id, 'No open Research case observed') : unknown,
    currentCaseTopic: memoryLive ? text(currentCase?.topic, 'No current case topic recorded') : unknown,
    currentCaseStatus: memoryLive ? text(currentCase?.status, 'No current case status recorded') : unknown,
    currentCaseNextAction: memoryLive ? text(currentCase?.next_action, 'No case next action recorded') : unknown,
    findings24h: findingLive ? recentFindings.length : unknown,
    handoffs24h: handoffLive ? handoffRows.filter((row) => recent(row, ['created_at', 'updated_at'])).length : unknown,
    proactiveObjectives: memoryLive ? objectiveIds.size : unknown,
    queries24h: memoryLive ? queries.length : unknown,
    queryFamilies24h: memoryLive ? new Set(queries.map((row) => row.query_family).filter(Boolean)).size : unknown,
    repeatSkips24h: memoryLive ? recentMemory.filter((row) => row.memory_kind === 'REPEAT_QUERY_SKIP').length : unknown,
    novelResults24h: memoryLive ? queries.reduce((sum, row) => sum + Number(row.new_results || 0), 0) : unknown,
    duplicates24h: memoryLive ? queries.reduce((sum, row) => sum + Number(row.duplicate_results || 0), 0) : unknown,
    saturatedFamilies: memoryLive ? new Set(memoryRecords.filter((row) => String(row.saturation_state || '').toUpperCase() === 'SATURATED').map((row) => row.query_family).filter(Boolean)).size : unknown,
    openBranches: memoryLive ? caseRows.filter((row) => (row.payload as Row | undefined)?.parent_case_id || row.parent_case_id).length : unknown,
    currentFamily: memoryLive ? text(current?.query_family, 'No proactive query observed') : unknown,
    nextQueryDirection: memoryLive ? text(current?.next_query_direction, 'No next direction recorded') : unknown,
    notebookWorkspaces: notebookLive ? notebooks.filter((row) => !['CLOSED', 'COMPLETED'].includes(String(row.status || '').toUpperCase())).length : unknown,
    researchFollowups: followups,
  };
}

export function buildDepartmentStatuses(work: GovernedWorkItem[], approvals: ExecutiveApprovalItem[], handoffs: CompanyHandoff[] = [], liveEvidence = false): DepartmentStatus[] {
  const departments = [
    ['research', 'Research', 'Continuous discovery, source analysis, durable findings, and handoffs.'],
    ['opportunities', 'Opportunities', 'Turn qualified intelligence into testable revenue opportunities.'],
    ['finance', 'Finance', 'Review sourced revenue, cost, and unit-economics evidence.'],
    ['trading', 'Trading', 'Turn trading knowledge into tested strategies; execution remains practice only.'],
    ['marketing', 'Marketing', 'Turn validated demand and offers into measured campaign plans.'],
    ['creative', 'Creative', 'Produce and revise usable campaign assets.'],
    ['labs', 'Labs', 'Run bounded technology and product experiments.'],
    ['upgrade_control', 'Upgrade Control', 'Review evidence and control production promotion.'],
    ['systems', 'Systems', 'Restore safe operational capability and verify recovery.'],
  ] as const;
  return departments.map(([departmentId, displayName, purpose]) => {
    const rows = work.filter((item) => departmentMatches(departmentId, item.department));
    const open = rows.filter((item) => !['COMPLETED', 'CANCELLED'].includes(item.lifecycle));
    const current = open.find((item) => item.lifecycle === 'RUNNING') || open[0];
    const pendingApprovals = approvals.filter((item) => departmentMatches(departmentId, item.department) && item.state === 'PENDING').length;
    const inRows = handoffs.filter((item) => departmentMatches(departmentId, item.targetDepartment));
    const outRows = handoffs.filter((item) => departmentMatches(departmentId, item.sourceDepartment));
    const activeHandoffs = inRows.filter((item) => !['COMPLETED', 'FAILED_FINAL', 'CANCELLED'].includes(item.status.toUpperCase()));
    const waitingHuman = rows.filter((item) => item.lifecycle === 'AWAITING_APPROVAL').length + pendingApprovals;
    const blockers = [...new Set(rows.filter((item) => ['BLOCKED', 'FAILED'].includes(item.lifecycle)).map((item) => item.blocker || item.lifecycle))];
    const status: DepartmentStatus['currentStatus'] = !liveEvidence ? 'NOT_PROVEN' : blockers.length ? 'BLOCKED' : current?.lifecycle === 'RUNNING' ? 'ACTIVE' : open.length ? 'PARTIAL' : 'IDLE';
    const relevantHandoff = [...activeHandoffs, ...inRows, ...outRows].sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')))[0];
    const currentHandoff = [...activeHandoffs].sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')))[0];
    const activeGoals = new Set([...activeHandoffs.map((item) => item.currentGoal), current?.goalId]
      .filter((value) => value && value !== 'Not attached' && value !== 'NOT_CONNECTED'));
    const currentWorkGoal = current?.goalId && current.goalId !== 'NOT_CONNECTED' ? current.goalId : null;
    const latestWork = [...rows].sort((a, b) => String(b.updatedAt || b.createdAt || '').localeCompare(String(a.updatedAt || a.createdAt || '')))[0];
    const latestCompleted = rows.filter((item) => item.lifecycle === 'COMPLETED')
      .sort((a, b) => String(b.updatedAt || b.createdAt || '').localeCompare(String(a.updatedAt || a.createdAt || '')))[0];
    const completedCutoff = Date.now() - 24 * 60 * 60 * 1000;
    const completedLast24h = rows.filter((item) => item.lifecycle === 'COMPLETED' && Date.parse(String(item.updatedAt || item.createdAt || '')) >= completedCutoff).length
      + inRows.filter((item) => item.status.toUpperCase() === 'COMPLETED' && Date.parse(String(item.createdAt || '')) >= completedCutoff).length;
    return {
      departmentId,
      displayName,
      purpose,
      currentStatus: status,
      owner: `${displayName} AI worker`,
      activeCapabilities: [],
      activeGovernedWork: open.length,
      activeGoals: activeGoals.size,
      currentGoal: currentHandoff?.currentGoal || currentWorkGoal || 'No active goal evidenced',
      evidenceRequest: current?.evidenceRequest || 'UNAVAILABLE',
      currentWork: current?.title || currentHandoff?.subject || 'No active governed work item',
      currentWorkItem: current?.id || currentHandoff?.workOrderId || 'No current work item evidenced',
      currentStage: currentHandoff?.currentStage || current?.lifecycle || 'No stage evidenced',
      currentAction: currentHandoff?.currentAction || current?.nextAction || 'No live action recorded',
      lastAction: latestWork?.title || latestCompleted?.title || relevantHandoff?.subject || 'No action recorded',
      nextAction: currentHandoff?.currentAction || current?.nextAction || latestCompleted?.nextAction || 'Derive from the active goal on the next operator cycle',
      lastResult: current?.blocker || latestCompleted?.executionStatus || relevantHandoff?.outcome || 'No recent result recorded',
      valueOutput: latestCompleted?.executionStatus || relevantHandoff?.outcome || 'No verified value/output recorded',
      completedLast24h,
      handoffsIn: inRows.length,
      handoffsOut: outRows.length,
      waitingHuman,
      lastActivityAt: latestWork?.updatedAt || latestWork?.createdAt || relevantHandoff?.createdAt || null,
      pendingApprovals,
      blockers,
      kpis: [`${open.length} open`, `${blockers.length} blocked`, `${pendingApprovals} approvals`, `${inRows.length} handoffs in`],
      activationState: liveEvidence ? 'LIVE WORK READ MODEL' : 'LIVE STATUS NOT PROVEN',
      evidence: evidence(liveEvidence ? 'LIVE' : 'UNKNOWN', liveEvidence ? 'Supabase task_requests / nexus_department_handoffs' : 'Live department evidence unavailable', liveEvidence ? 'HIGH' : 'LOW'),
    };
  });
}

export function buildRepoIntelligenceItems(): RepoIntelligenceItem[] {
  const candidates = Array.isArray((repoRegistry as { candidates?: unknown[] }).candidates) ? (repoRegistry as { candidates: Row[] }).candidates : [];
  const normalized = candidates.map((candidate) => ({
    candidateId: text(candidate.candidate_id, 'unknown'),
    repository: `${text(candidate.repository_owner, 'unknown')}/${text(candidate.repository_name, 'unknown')}`,
    category: text(candidate.category, 'unknown'),
    license: text(candidate.license, 'UNKNOWN'),
    maintenanceStatus: text(candidate.maintenance_status, 'UNKNOWN'),
    securityStatus: Array.isArray(candidate.security_advisories) ? (candidate.security_advisories as unknown[]).join(', ') : 'UNKNOWN',
    nexusOverlap: Array.isArray(candidate.existing_nexus_overlap) ? (candidate.existing_nexus_overlap as unknown[]).map(String) : [],
    candidateStatus: text(candidate.candidate_status, 'UNKNOWN'),
    proposedDisposition: text(candidate.proposed_disposition, 'DEFER'),
    blueprintWave: text(candidate.blueprint_wave, 'UNKNOWN'),
    decisionRequired: text(candidate.ray_decision, 'PENDING'),
    evidenceLinks: Array.isArray(candidate.evidence_links) ? (candidate.evidence_links as unknown[]).map(String) : [],
    accessProfile: text(candidate.initial_mode ?? candidate.access_profile, ''),
  }));
  return normalized;
}

export function buildSystemHealth(): ExecutiveHealthItem[] {
  const connectors = getConnectorRegistry();
  const safety = connectorSafetyInvariants();
  const health: ExecutiveHealthItem[] = [
    {
      component: 'Stripe live payments',
      category: 'revenue',
      status: 'DEFERRED',
      source: 'Owner policy',
      impact: 'No live checkout until Nexus 3.0 completion and Ray approval',
      owner: 'Ray Davis',
      recommendedAction: 'Keep STRIPE_MODE=test',
      evidence: evidence('DEFERRED', 'Stripe policy in Wave 1 prompt', 'HIGH'),
    },
    {
      component: 'Live trading',
      category: 'trading',
      status: 'BLOCKED_BY_POLICY',
      source: 'Trading protection policy',
      impact: 'No broker orders or funded trading from Nexus',
      owner: 'Ray Davis',
      recommendedAction: 'Keep trading read-only/paper-only',
      evidence: evidence('BLOCKED', 'Nexus safety policy', 'HIGH'),
    },
    {
      component: 'Alpha Supabase access',
      category: 'research',
      status: safety.alphaSupabase ? 'BLOCKED' : 'PROHIBITED',
      source: 'Alpha no-Supabase guard',
      impact: 'Protects client and company data from unrestricted research layer',
      owner: 'Engineering',
      recommendedAction: 'Preserve no-Supabase guard',
      evidence: evidence('REPORT_BACKED', 'src/hermes/alpha/noSupabaseGuard.ts', 'HIGH'),
    },
  ];
  connectors.slice(0, 8).forEach((connector) => {
    health.push({
      component: connector.name,
      category: connector.feature,
      status: connector.status === 'configured_safe' ? 'HEALTHY' : connector.status === 'future_only' ? 'DEFERRED' : connector.status === 'blocked' ? 'BLOCKED' : 'UNKNOWN',
      source: 'Connector registry',
      impact: connector.notes ?? connector.purpose,
      owner: connector.approvalRequired ? 'Ray approval required' : 'Engineering',
      recommendedAction: connector.requiredNow ? 'Maintain' : connector.notes ?? 'Review only when this capability is prioritized',
      evidence: evidence('REPORT_BACKED', 'src/hermes/nexus/nexusConnectorRegistry.ts', 'MEDIUM'),
    });
  });
  return health;
}

function metric(id: string, label: string, value: string | number, status: string, priority: ExecutiveMetric['priority'], source: ExecutiveEvidence): ExecutiveMetric {
  return { id, label, value, status, priority, evidence: source };
}

function buildCapabilitySummary() {
  const summary = buildCapabilityOSSummary();
  const priorityModes = ['PROHIBITED', 'BLOCKED_BY_POLICY', 'DEFERRED', 'NOT_CONFIGURED', 'APPROVAL_GATED', 'TEST_ONLY', 'READ_ONLY', 'ACTIVE'];
  const topCapabilities = [...summary.capabilities]
    .sort((a, b) => {
      const aScore = priorityModes.indexOf(a.activationMode);
      const bScore = priorityModes.indexOf(b.activationMode);
      return (aScore === -1 ? 99 : aScore) - (bScore === -1 ? 99 : bScore);
    })
    .slice(0, 12)
    .map((capability) => ({
      capabilityId: capability.capabilityId,
      name: capability.name,
      departmentId: capability.departmentId,
      activationMode: capability.activationMode,
      approvalLevel: capability.approvalLevel,
      healthStatus: capability.healthStatus,
      credentialRequirements: capability.credentialRequirements,
      dependencies: capability.dependencies,
      rayApprovalState: capability.rayApprovalState,
    }));
  return {
    total: summary.total,
    byActivationMode: summary.byActivationMode,
    byHealth: summary.byHealth,
    approvalGated: summary.approvalGated,
    awaitingRayApproval: summary.awaitingRayApproval,
    missingCredentials: summary.missingCredentials,
    dependencyBlocked: summary.dependencyBlocked,
    proposals: summary.proposals.length,
    topCapabilities,
  };
}

function buildKnowledgeSummary() {
  const summary = buildKnowledgeHealthSummary();
  return {
    totalRecords: summary.totalRecords,
    approvedKnowledge: summary.approvedKnowledge,
    unverifiedClaims: summary.unverifiedClaims,
    staleRecords: summary.staleRecords,
    expiredRecords: summary.expiredRecords,
    conflicts: summary.conflicts,
    missingProvenance: summary.missingProvenance,
    pendingReviews: summary.pendingReviews,
    rejectedFindings: summary.rejectedFindings,
    recordsBlockedByPolicy: summary.recordsBlockedByPolicy,
    alphaSubmissionsAwaitingReview: summary.alphaSubmissionsAwaitingReview,
    clientSafeKnowledge: summary.clientSafeKnowledge,
    brainProfiles: summary.brainProfiles,
    activeBrains: summary.activeBrains,
    plannedDepartmentTemplates: summary.plannedDepartmentTemplates,
    retrievalDenials: summary.retrievalDenials,
    documentEvidenceStatus: summary.documentEvidenceStatus,
    evaluationPassed: summary.evaluationPassed,
    evaluationTotal: summary.evaluationTotal,
  };
}

function buildBrainSummary() {
  return getBrainProfiles().map((profile) => ({
    brainId: profile.brainId,
    name: profile.name,
    role: profile.role,
    status: profile.status,
    departmentId: profile.departmentId,
    mayUseSupabase: profile.mayUseSupabase,
    mayUseWeb: profile.mayUseWeb,
    mayAccessClientPii: profile.mayAccessClientPii,
    mayApproveKnowledge: profile.mayApproveKnowledge,
    mayExecuteWork: profile.mayExecuteWork,
    requiredApprovalLevel: profile.requiredApprovalLevel,
    allowedCapabilities: profile.allowedCapabilities,
    prohibitedDataClasses: profile.prohibitedDataClasses,
  }));
}

function buildBrief(state: Omit<ExecutiveCommandCenterState, 'dailyBrief'>): ExecutiveBrief {
  const urgent = state.topActions.filter((item) => item.priority === 'P0' || item.priority === 'P1');
  return {
    generatedAt: state.generatedAt,
    sections: [
      {
        id: 'protect_company',
        title: 'Company protection',
        facts: ['Stripe live mode is deferred', 'Live trading is blocked by policy', `${state.systemHealth.length} health items normalized`],
        interpretations: ['The primary risk is activating external systems before approval.'],
        recommendations: ['Keep live Stripe, live trading, external publishing, and unrestricted Alpha access disabled.'],
        unknowns: [],
        blockedData: [],
      },
      {
        id: 'customers',
        title: 'Customer protection and service',
        facts: state.customerSummary.map((item) => `${item.label}: ${item.value}`),
        interpretations: ['Customer views should stay aggregate in Founder Mode unless Ray opens an admin detail view.'],
        recommendations: ['Monitor document-processing depth because it remains certified but needs recheck.'],
        unknowns: state.customerSummary.some((item) => item.evidence.state === 'BLOCKED') ? ['Live customer rows require authenticated admin session.'] : [],
        blockedData: [],
      },
      {
        id: 'revenue',
        title: 'Revenue',
        facts: state.revenueSummary.map((item) => `${item.label}: ${item.value}`),
        interpretations: ['Test-mode revenue is certified; live revenue is intentionally not enabled.'],
        recommendations: ['Use test-mode evidence until Ray approves live configuration after Nexus 3.0 completion.'],
        unknowns: [],
        blockedData: ['Live Stripe credentials and live webhook are intentionally not configured.'],
      },
      {
        id: 'operations',
        title: 'Operations',
        facts: [`${state.approvals.length} normalized approvals`, `${state.governedWork.length} governed work records`, `${state.departments.length} departments classified`],
        interpretations: ['The canonical chain is task_requests to approvals to agent_jobs to nexus_events.'],
        recommendations: urgent.slice(0, 3).map((item) => item.title),
        unknowns: [],
        blockedData: [],
      },
      {
        id: 'research',
        title: 'Research and expansion',
        facts: [`${state.repoIntelligence.length} repo-intelligence candidates`, `${state.knowledgeHealth?.unverifiedClaims ?? 0} unverified claims`, `${state.brainProfiles?.length ?? 0} brain profiles`, 'No external repository installation is approved.'],
        interpretations: ['Repo intelligence is a read-only research lane with Ray Review hooks only; Alpha claims do not become Hermes facts automatically.'],
        recommendations: ['Review candidates with UNKNOWN or restrictive license status before any future integration.'],
        unknowns: state.repoIntelligence.filter((item) => item.license === 'UNKNOWN' || item.license === 'NOASSERTION').slice(0, 3).map((item) => `${item.repository} license/security`),
        blockedData: [],
      },
      {
        id: 'decisions',
        title: 'Decisions required from Ray',
        facts: state.repoIntelligence.filter((item) => item.decisionRequired === 'PENDING').slice(0, 5).map((item) => `${item.repository}: ${item.proposedDisposition}`),
        interpretations: ['Decisions should approve research disposition only, not installation.'],
        recommendations: state.topActions.slice(0, 3).map((item) => item.title),
        unknowns: [],
        blockedData: [],
      },
    ],
  };
}

export async function loadExecutiveCommandCenterState(): Promise<ExecutiveCommandCenterState> {
  const generatedAt = nowIso();
  const [approvalsResult, tasksResult, jobsResult, eventsResult, clientsResult, documentsResult, ordersResult, fulfillmentsResult, healthResult, handoffsResult, researchSourcesResult, proactiveMemoryResult, researchQuestionsResult, researchFindingsResult, researchNotebooksResult, researchFollowupsResult] = await Promise.all([
    listTableDetailed<Row>('approvals', { limit: 100 }),
    listTableDetailed<Row>('task_requests', { limit: 100 }),
    listTableDetailed<Row>('agent_jobs', { limit: 100 }),
    listTableDetailed<Row>('nexus_events', { limit: 100 }),
    listTableDetailed<Row>('client_profiles', { limit: 100 }),
    listTableDetailed<Row>('client_documents', { limit: 100 }),
    listTableDetailed<Row>('client_orders', { limit: 100 }),
    listTableDetailed<Row>('service_fulfillments', { limit: 100 }),
    listTableDetailed<Row>('system_health', { limit: 100 }),
    listTableDetailed<Row>('nexus_department_handoffs', { limit: 100 }),
    listTableDetailed<Row>('research_sources', { limit: 500 }),
    listTableDetailed<Row>('research_proactive_memory', { limit: 500 }),
    listTableDetailed<Row>('research_questions', { limit: 100 }),
    listTableDetailed<Row>('research_findings', { limit: 100 }),
    listTableDetailed<Row>('research_notebooks', { limit: 100 }),
    listTableDetailed<Row>('department_research_requests', { limit: 100 }),
  ]);

  const approvalRows = approvalsResult.data.length ? approvalsResult.data : tasksResult.data.filter((row) => text(row.task_type, '').includes('ray_review'));
  const approvals = normalizeApprovalRows(approvalRows, sourceFromResult(approvalsResult.data.length ? approvalsResult : tasksResult, approvalsResult.data.length ? 'approvals' : 'task_requests'));
  const governedWork = normalizeGovernedWorkRows(tasksResult.data, approvalsResult.data, jobsResult.data, sourceFromResult(tasksResult, 'task_requests'));
  const handoffs = normalizeCompanyHandoffs(handoffsResult.data);
  const runtimeReadOk = ['connected_with_records', 'no_records'].includes(tasksResult.status)
    && ['connected_with_records', 'no_records'].includes(handoffsResult.status);
  const departments = buildDepartmentStatuses(governedWork, approvals, handoffs, runtimeReadOk);
  const liveStatus = (result: TableQueryResult<Row>) => ['connected_with_records', 'no_records'].includes(result.status) ? 'LIVE' : result.status.toUpperCase();
  const researchObservability = buildResearchObservability(researchSourcesResult.data, proactiveMemoryResult.data,
    researchQuestionsResult.data, researchFindingsResult.data, researchNotebooksResult.data, handoffsResult.data, {
      sources: liveStatus(researchSourcesResult), memory: liveStatus(proactiveMemoryResult),
      questions: liveStatus(researchQuestionsResult), findings: liveStatus(researchFindingsResult),
      notebooks: liveStatus(researchNotebooksResult), handoffs: liveStatus(handoffsResult),
      followups: liveStatus(researchFollowupsResult),
    }, researchFollowupsResult.data);
  const repoIntelligence = buildRepoIntelligenceItems();
  const systemHealth = [
    ...buildSystemHealth(),
    ...healthResult.data.slice(0, 10).map((row) => ({
      component: text(row.component ?? row.name, 'System component'),
      category: text(row.category ?? row.lane, 'system'),
      status: String(row.status ?? 'UNKNOWN').toUpperCase() as ExecutiveHealthItem['status'],
      source: 'Supabase system_health',
      impact: text(row.summary ?? row.message, 'No impact summary recorded'),
      owner: text(row.owner, 'Operations'),
      recommendedAction: text(row.recommended_action, 'Monitor'),
      evidence: sourceFromResult(healthResult, 'system_health'),
    })),
  ];

  const customerEvidence = sourceFromResult(clientsResult, 'client_profiles');
  const revenueEvidence = sourceFromResult(ordersResult, 'client_orders');
  const capabilityOS = buildCapabilitySummary();
  const knowledgeHealth = buildKnowledgeSummary();
  const brainProfiles = buildBrainSummary();
  const metrics: ExecutiveMetric[] = [
    metric('pending_approvals', 'Pending approvals', approvals.filter((item) => item.state === 'PENDING').length, 'Ray decision queue', 'P0', approvals[0]?.evidence ?? sourceFromResult(approvalsResult, 'approvals')),
    metric('blocked_work', 'Blocked work', governedWork.filter((item) => item.lifecycle === 'BLOCKED' || item.lifecycle === 'FAILED').length, 'Governed execution', 'P0', sourceFromResult(tasksResult, 'task_requests')),
    metric('customer_records', 'Customer records', clientsResult.resultCount, clientsResult.status, 'P1', customerEvidence),
    metric('test_orders', 'Order records', ordersResult.resultCount, 'Test/live labeled revenue records', 'P2', revenueEvidence),
    metric('repo_candidates', 'Repo candidates', repoIntelligence.length, 'Read-only research lane', 'P4', evidence('UNKNOWN', 'No governed production repo-intelligence source', 'MEDIUM')),
    metric('capabilities', 'Capabilities governed', capabilityOS.total, `${capabilityOS.approvalGated} approval-gated`, 'P3', evidence('REPORT_BACKED', 'Capability OS registry', 'HIGH')),
    metric('knowledge_records', 'Knowledge records', knowledgeHealth.totalRecords, `${knowledgeHealth.pendingReviews} reviews pending`, 'P3', evidence('REPORT_BACKED', 'Knowledge Intelligence registry', 'HIGH')),
  ];
  const customerSummary: ExecutiveMetric[] = [
    metric('active_clients', 'Active test clients', clientsResult.resultCount, clientsResult.status, 'P1', customerEvidence),
    metric('documents', 'Document records', documentsResult.resultCount, documentsResult.status, 'P1', sourceFromResult(documentsResult, 'client_documents')),
    metric('customer_action', 'Items awaiting customer/admin action', governedWork.filter((item) => /customer|client|review/i.test(item.department)).length, 'Derived from governed work', 'P1', sourceFromResult(tasksResult, 'task_requests')),
    metric('recent_events', 'Recent workflow events', eventsResult.resultCount, eventsResult.status, 'P3', sourceFromResult(eventsResult, 'nexus_events')),
  ];
  const revenueSummary: ExecutiveMetric[] = [
    metric('stripe_mode', 'Stripe mode', 'TEST', 'LIVE STRIPE CONFIGURATION DEFERRED UNTIL NEXUS 3.0 COMPLETION', 'P2', evidence('DEFERRED', 'Wave 1 Stripe policy', 'HIGH')),
    metric('orders', 'Order records', ordersResult.resultCount, ordersResult.status, 'P2', revenueEvidence),
    metric('fulfillments', 'Fulfillment records', fulfillmentsResult.resultCount, fulfillmentsResult.status, 'P2', sourceFromResult(fulfillmentsResult, 'service_fulfillments')),
    metric('projected_revenue', 'Projected revenue', 'REPORT_BACKED', 'Not collected revenue', 'P2', evidence('REPORT_BACKED', 'reports/research/nexus_money_engine_recommendations.md', 'MEDIUM')),
  ];
  const topActions: ExecutiveActionItem[] = [
    {
      id: 'protect_external_actions',
      title: 'Keep external actions approval-gated',
      reason: 'Live Stripe, live trading, publishing, sending, and repository write access are not approved.',
      priority: 'P0',
      status: 'Required guardrail',
      route: 'rayreview',
      evidence: evidence('DEFERRED', 'Wave 1 safety policy', 'HIGH'),
    },
    {
      id: 'review_pending_approvals',
      title: approvals.filter((item) => item.state === 'PENDING').length ? 'Review pending Ray approvals' : 'Confirm Ray Review queue is clear',
      reason: 'Approvals are the decision authority before execution.',
      priority: 'P0',
      status: `${approvals.filter((item) => item.state === 'PENDING').length} pending`,
      route: 'rayreview',
      evidence: approvals[0]?.evidence ?? sourceFromResult(approvalsResult, 'approvals'),
    },
    {
      id: 'watch_customer_operations',
      title: 'Monitor customer workflow evidence',
      reason: 'Document-processing depth remains certified but needs recheck.',
      priority: 'P1',
      status: clientsResult.status,
      route: 'clients',
      evidence: customerEvidence,
    },
  ];
  const withoutBrief = {
    generatedAt,
    phoenixDateTime: phoenixDateTime(),
    metrics,
    topActions,
    approvals,
    governedWork,
    departments,
    handoffs,
    handoffEvidenceStatus: handoffsResult.status,
    researchObservability,
    customerSummary,
    revenueSummary,
    systemHealth,
    repoIntelligence,
    capabilityOS,
    knowledgeHealth,
    brainProfiles,
    limitations: [
      'Read-only executive aggregation; no external action execution.',
      'Live Stripe configuration deferred by owner.',
      'Repo Intelligence is visible but cannot install or copy external code.',
      'No new database tables were created in Wave 1.',
      'Wave 3 uses version-controlled intelligence and brain policy with existing approval chains; no new database tables were created.',
    ],
  };
  return { ...withoutBrief, dailyBrief: buildBrief(withoutBrief) };
}

export function getExecutiveCommandCenterSnapshot(): ExecutiveCommandCenterState {
  const generatedAt = nowIso();
  const repoIntelligence = buildRepoIntelligenceItems();
  const knowledgeHealth = buildKnowledgeSummary();
  const brainProfiles = buildBrainSummary();
  const governedWork: GovernedWorkItem[] = [];
  const approvals: ExecutiveApprovalItem[] = [];
  const departments = buildDepartmentStatuses(governedWork, approvals);
  const systemHealth = buildSystemHealth();
  const metrics: ExecutiveMetric[] = [
    metric('pending_approvals', 'Pending approvals', 'UNKNOWN', 'Requires authenticated admin session', 'P0', evidence('UNKNOWN', 'Supabase approvals')),
    metric('blocked_work', 'Blocked work', 'UNKNOWN', 'Requires authenticated admin session', 'P0', evidence('UNKNOWN', 'Supabase task_requests')),
    metric('customer_records', 'Customer records', 'UNKNOWN', 'Requires authenticated admin session', 'P1', evidence('UNKNOWN', 'Supabase client_profiles')),
    metric('stripe_mode', 'Stripe mode', 'TEST', 'Live deferred', 'P2', evidence('DEFERRED', 'Wave 1 Stripe policy', 'HIGH')),
    metric('repo_candidates', 'Repo candidates', repoIntelligence.length, 'Read-only research lane', 'P4', evidence('UNKNOWN', 'No governed production repo-intelligence source', 'MEDIUM')),
    metric('capabilities', 'Capabilities governed', buildCapabilitySummary().total, 'Capability OS read model', 'P3', evidence('REPORT_BACKED', 'Capability OS registry', 'HIGH')),
    metric('knowledge_records', 'Knowledge records', knowledgeHealth.totalRecords, `${knowledgeHealth.pendingReviews} reviews pending`, 'P3', evidence('REPORT_BACKED', 'Knowledge Intelligence registry', 'HIGH')),
  ];
  const topActions: ExecutiveActionItem[] = [
    {
      id: 'protect_external_actions',
      title: 'Keep external actions approval-gated',
      reason: 'No live Stripe, live trading, publishing, or repo installation is approved.',
      priority: 'P0',
      status: 'Active',
      route: 'rayreview',
      evidence: evidence('DEFERRED', 'Wave 1 safety policy', 'HIGH'),
    },
    {
      id: 'review_repo_intelligence',
      title: 'Review repo-intelligence decisions',
      reason: 'External repository candidates are research-only until Ray approves later integration.',
      priority: 'P4',
      status: `${repoIntelligence.length} candidates`,
      route: 'reports',
      evidence: evidence('UNKNOWN', 'No governed production repo-intelligence source', 'MEDIUM'),
    },
    {
      id: 'open_system_health',
      title: 'Open system health',
      reason: 'Health evidence is normalized but live records need authenticated read access.',
      priority: 'P0',
      status: 'Read-only',
      route: 'health',
      evidence: evidence('REPORT_BACKED', 'connector registry and system_health table', 'MEDIUM'),
    },
  ];
  const state = {
    generatedAt,
    phoenixDateTime: phoenixDateTime(),
    metrics,
    topActions,
    approvals,
    governedWork,
    departments,
    handoffs: [],
    handoffEvidenceStatus: 'no_authenticated_session',
    researchObservability: buildResearchObservability([], [], [], [], [], [], {
      sources: 'NO_AUTHENTICATED_SESSION', memory: 'NO_AUTHENTICATED_SESSION', questions: 'NO_AUTHENTICATED_SESSION',
      findings: 'NO_AUTHENTICATED_SESSION', notebooks: 'NO_AUTHENTICATED_SESSION', handoffs: 'NO_AUTHENTICATED_SESSION',
    }),
    customerSummary: [],
    revenueSummary: [metrics[3]],
    systemHealth,
    repoIntelligence,
    capabilityOS: buildCapabilitySummary(),
    knowledgeHealth,
    brainProfiles,
    limitations: [
      'Static snapshot used until authenticated admin session loads live Supabase summaries.',
      'Knowledge and brain profile records are governed read models; durable knowledge approval persistence is deferred to a later migration decision.',
    ],
  };
  return { ...state, dailyBrief: buildBrief(state) };
}
