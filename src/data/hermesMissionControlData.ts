import pilot from '../../reports/hermes_modernization/end_to_end_pilot.json';
import modernizationState from '../../reports/hermes_modernization/state.json';
import loopState from '../../data/runtime/nexus_loops/loop_state.json';

export type MissionStatus = 'PASS' | 'PARTIAL' | 'BLOCKED' | 'UNKNOWN' | string;
export const MISSION_WORKER_STATUSES = ['AVAILABLE', 'INSTALLED_UNPROVEN', 'AUTH_BLOCKED', 'RATE_LIMITED', 'NOT_INSTALLED', 'UNAVAILABLE'] as const;
export type MissionWorkerStatus = typeof MISSION_WORKER_STATUSES[number];

export function normalizeMissionControlWorkerStatus(value: unknown): MissionWorkerStatus | 'UNKNOWN' {
  return MISSION_WORKER_STATUSES.includes(String(value) as MissionWorkerStatus) ? String(value) as MissionWorkerStatus : 'UNKNOWN';
}

type Pilot = typeof pilot & {
  opportunity: {
    id: string;
    title: string;
    category: string;
    base_score: number;
    confidence: number;
    risk: number;
    status: string;
    recommended_next_action: string;
  };
  creative: {
    selected_territory: string;
    territory_count: number;
    status: string;
  };
  workers: Array<Record<string, unknown>>;
  ledger: Record<string, any>;
  tokens: Record<string, number>;
};

const source = pilot as Pilot;
const loop = (loopState as any).loops?.system_health_loop;
const lastLoop = loop?.last_run;
const systemSummary = lastLoop?.summary;

export const hermesMissionControlData = {
  phase: 'PHASE 10 — MISSION CONTROL V2 VISIBILITY',
  resumePoint: 'PHASE 10 — MISSION CONTROL V2 VISIBILITY',
  finalStatus: source.result,
  sourceCommit: source.ending_commit,
  opportunity: source.opportunity,
  activeOpportunityCount: 1,
  research: source.research,
  creative: source.creative,
  buildSpec: {
    status: source.creative.build_spec?.task_id ? 'PASS' : 'UNKNOWN',
    taskId: source.creative.build_spec?.task_id ?? 'UNKNOWN',
    objective: source.creative.build_spec?.objective ?? 'UNKNOWN',
  },
  workers: source.workers.map((worker) => ({
    id: String(worker.worker_id ?? 'UNKNOWN'),
    status: normalizeMissionControlWorkerStatus(worker.classification ?? worker.status),
    installed: worker.installed === true,
    reason: String(worker.availability_reason ?? 'UNKNOWN'),
  })),
  builder: {
    status: source.builder_status,
    workerUsed: source.worker_used,
    verification: source.verification_status,
    visualCheck: source.visual_check,
    retries: source.ledger?.retry_count ?? 0,
    testsPassed: source.ledger?.tests_passed ?? 0,
    testsFailed: source.ledger?.tests_failed ?? 0,
  },
  execution: {
    deterministicRatio: source.tokens.input === 0 && source.tokens.output === 0 ? '100%' : 'UNKNOWN',
    aiRatio: source.tokens.input === 0 && source.tokens.output === 0 ? '0%' : 'UNKNOWN',
    zeroTokenExecutions: source.tokens.zero_token_operations,
    inputTokens: source.tokens.input,
    outputTokens: source.tokens.output,
    providerCostUsd: source.tokens.provider_cost_usd,
    localComputeExecutions: source.tokens.local_compute_executions,
  },
  approvals: {
    pending: typeof systemSummary?.pending_approvals === 'number' ? systemSummary.pending_approvals : 'UNKNOWN',
    source: lastLoop?.source_caps?.includes('get_pending_approvals') ? 'system_health_loop' : 'UNKNOWN',
  },
  loops: {
    systemHealth: lastLoop?.status ?? 'UNKNOWN',
    systemStatus: systemSummary?.system_status ?? 'UNKNOWN',
    activeRuns: systemSummary?.active_runs ?? 'UNKNOWN',
    failedRuns: systemSummary?.failed_runs ?? 'UNKNOWN',
    lastUpdated: loop?.last_updated_at ?? 'UNKNOWN',
  },
  modernizationState,
} as const;

export type HermesMissionControlData = typeof hermesMissionControlData;
