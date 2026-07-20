import { runCapabilityPreflight } from '../capabilities/capabilityPreflight';
import type { CapabilityDataClass } from '../capabilities/capabilityTypes';

export type OperationMode = 'READ_ONLY' | 'ADVISORY' | 'DRAFT_ONLY' | 'APPROVAL_GATED' | 'BOUNDED_EXECUTION';
export type DepartmentStatusState = 'ACTIVE' | 'DEGRADED' | 'PAUSED' | 'NOT_CONFIGURED';
export type QueuePriority = 'P0_COMPANY' | 'P1_CUSTOMER' | 'P2_REVENUE' | 'P3_OPERATIONS' | 'P4_RESEARCH';
export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type QueueStatus = 'NEW' | 'TRIAGED' | 'PLANNED' | 'AWAITING_APPROVAL' | 'READY' | 'IN_PROGRESS' | 'BLOCKED' | 'VERIFYING' | 'COMPLETE' | 'CANCELLED' | 'ESCALATED';
export type BlockerType = 'DEPENDENCY' | 'APPROVAL' | 'CREDENTIAL' | 'POLICY' | 'DATA' | 'SYSTEM_HEALTH' | 'EXTERNAL_SERVICE' | 'HUMAN_DECISION' | 'UNKNOWN';
export type IncidentStatus = 'DETECTED' | 'TRIAGED' | 'CONTAINED' | 'REPAIR_PLANNED' | 'AWAITING_APPROVAL' | 'REPAIRING' | 'VERIFYING' | 'RESOLVED' | 'POSTMORTEM_REQUIRED' | 'CLOSED';

export interface NexusDepartmentDefinition {
  departmentId: string;
  name: string;
  description: string;
  ownerRole: string;
  executiveCoordinator: 'hermes';
  defaultOperationMode: OperationMode;
  allowedCapabilityIds: string[];
  prohibitedCapabilityIds: string[];
  allowedDataClasses: CapabilityDataClass[];
  prohibitedDataClasses: CapabilityDataClass[];
  intakeSources: string[];
  escalationTargets: string[];
  serviceLevelPolicy: { acknowledgementTargetMinutes?: number; reviewTargetHours?: number; resolutionTargetHours?: number };
  healthSource: string;
  status: DepartmentStatusState;
}

export interface DepartmentQueueItem {
  itemId: string;
  departmentId: string;
  title: string;
  summary: string;
  sourceType: string;
  sourceId?: string;
  priority: QueuePriority;
  urgency: Severity;
  riskLevel: Severity;
  operationMode: OperationMode;
  status: QueueStatus;
  ownerRole?: string;
  assignedActorId?: string;
  capabilityIds: string[];
  dependencyIds: string[];
  blockerIds: string[];
  requiresApproval: boolean;
  approvalId?: string;
  evidenceIds: string[];
  completionCriteria: string[];
  createdAt: string;
  updatedAt: string;
  dueAt?: string;
  synthetic: boolean;
}

export interface DepartmentBlocker {
  blockerId: string;
  departmentId: string;
  title: string;
  description: string;
  blockerType: BlockerType;
  severity: Severity;
  status: 'OPEN' | 'MITIGATED' | 'RESOLVED' | 'ACCEPTED';
  affectedItemIds: string[];
  ownerRole?: string;
  mitigation?: string;
  evidenceIds: string[];
  createdAt: string;
  resolvedAt?: string;
}

export interface DepartmentIncident {
  incidentId: string;
  departmentId: string;
  title: string;
  status: IncidentStatus;
  impact: string;
  affectedSystems: string[];
  currentState: string;
  containment: string;
  ownerRole: string;
  nextAction: string;
  evidenceIds: string[];
  verification: string;
  createdAt: string;
  updatedAt: string;
}

export interface WorkVerification {
  verificationId: string;
  queueItemId: string;
  criteriaResults: Array<{ criterion: string; passed: boolean; evidenceIds: string[] }>;
  verifiedBy: string;
  verifiedAt: string;
  result: 'PASS' | 'FAIL' | 'PARTIAL';
  notes?: string;
}

export interface GovernedExecutionPlan {
  executionId: string;
  queueItemId: string;
  capabilityId: string;
  operationMode: 'BOUNDED_EXECUTION';
  approvedScope: string[];
  prohibitedScope: string[];
  maximumOperations: number;
  timeLimitMinutes: number;
  costLimit?: number;
  preconditions: string[];
  completionCriteria: string[];
  rollbackPlan: string[];
  approvalId: string;
  approvedBy: string;
  approvedAt: string;
  status: 'READY' | 'RUNNING' | 'PAUSED' | 'COMPLETE' | 'FAILED' | 'ROLLED_BACK' | 'EXPIRED';
  evidenceIds: string[];
}

export interface DepartmentHealth {
  departmentId: string;
  state: 'HEALTHY' | 'DEGRADED' | 'BLOCKED' | 'PAUSED' | 'NOT_CONFIGURED';
  openItems: number;
  criticalItems: number;
  blockedItems: number;
  awaitingApproval: number;
  overdueItems: number;
  oldestOpenItemAgeHours?: number;
  completionRate?: number;
  topRisks: string[];
  topBlockers: string[];
  observedAt: string;
}

export interface DepartmentOperationsSnapshot {
  generatedAt: string;
  departments: NexusDepartmentDefinition[];
  queueItems: DepartmentQueueItem[];
  blockers: DepartmentBlocker[];
  incidents: DepartmentIncident[];
  verifications: WorkVerification[];
  executionPlans: GovernedExecutionPlan[];
  health: DepartmentHealth[];
  evidenceIds: string[];
  limitations: string[];
}

const now = () => new Date().toISOString();
const hoursAgo = (hours: number) => new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

export const activeDepartmentRegistry: NexusDepartmentDefinition[] = [
  { departmentId: 'operations', name: 'Operations', description: 'System coordination, queue health, blocker escalation, approval follow-up, incidents, and cross-department dependencies.', ownerRole: 'Operations Coordinator', executiveCoordinator: 'hermes', defaultOperationMode: 'ADVISORY', allowedCapabilityIds: ['hermes_work_summary_tool', 'hermes_approval_summary_tool', 'executive_command_center', 'nexus_clean_worktree_gate'], prohibitedCapabilityIds: ['live_trading_execution', 'stripe_live_activation'], allowedDataClasses: ['INTERNAL_METADATA', 'CLIENT_AGGREGATE'], prohibitedDataClasses: ['CLIENT_PII', 'CREDENTIALS', 'PRODUCTION_CONTROL'], intakeSources: ['Hermes', 'Executive Command Center', 'Ray Review', 'system health', 'governed work'], escalationTargets: ['Ray Review', 'Engineering Lead', 'Knowledge Steward'], serviceLevelPolicy: { acknowledgementTargetMinutes: 30, reviewTargetHours: 4, resolutionTargetHours: 48 }, healthSource: 'src/lib/departments/departmentOperations.ts', status: 'ACTIVE' },
  { departmentId: 'engineering', name: 'Engineering', description: 'Bugs, build failures, deployment issues, technical debt, integration readiness, and security repairs.', ownerRole: 'Engineering Lead', executiveCoordinator: 'hermes', defaultOperationMode: 'DRAFT_ONLY', allowedCapabilityIds: ['authenticated_playwright', 'hermes_production_certification', 'capability_os_registry', 'nexus_clean_worktree_gate'], prohibitedCapabilityIds: ['live_trading_execution', 'stripe_live_activation'], allowedDataClasses: ['INTERNAL_METADATA', 'CLIENT_AGGREGATE'], prohibitedDataClasses: ['CLIENT_PII', 'CREDENTIALS', 'PRODUCTION_CONTROL'], intakeSources: ['test failures', 'build logs', 'Hermes reports', 'production browser certification'], escalationTargets: ['Ray Review', 'Operations Coordinator'], serviceLevelPolicy: { acknowledgementTargetMinutes: 30, reviewTargetHours: 4, resolutionTargetHours: 72 }, healthSource: 'TypeScript, build, Playwright, RLS harness', status: 'ACTIVE' },
  { departmentId: 'research', name: 'Research', description: 'Public-source research requests, opportunity investigation, comparison studies, evidence collection, and Alpha handoff.', ownerRole: 'Research Lead', executiveCoordinator: 'hermes', defaultOperationMode: 'ADVISORY', allowedCapabilityIds: ['hermes_research_handoff', 'hermes_report_catalog_tool', 'repo_intelligence_candidate_registry'], prohibitedCapabilityIds: ['alpha_supabase_access', 'external_writer_tools'], allowedDataClasses: ['PUBLIC_DATA', 'INTERNAL_METADATA'], prohibitedDataClasses: ['CLIENT_PII', 'CREDENTIALS', 'PRODUCTION_CONTROL'], intakeSources: ['Alpha research', 'repo intelligence', 'approved reports'], escalationTargets: ['Knowledge Steward', 'Ray Review'], serviceLevelPolicy: { acknowledgementTargetMinutes: 60, reviewTargetHours: 24, resolutionTargetHours: 120 }, healthSource: 'reports/runtime/nexus_repo_intelligence_registry.json', status: 'ACTIVE' },
  { departmentId: 'knowledge', name: 'Knowledge', description: 'Approved knowledge, report indexing, provenance, stale evidence, conflict detection, policy records, and retrieval quality.', ownerRole: 'Knowledge Steward', executiveCoordinator: 'hermes', defaultOperationMode: 'READ_ONLY', allowedCapabilityIds: ['hermes_report_catalog_tool', 'hermes_provenance_tool', 'knowledge_layer'], prohibitedCapabilityIds: ['unreviewed_publication', 'external_writer_tools'], allowedDataClasses: ['INTERNAL_METADATA', 'PUBLIC_DATA'], prohibitedDataClasses: ['CLIENT_PII', 'CREDENTIALS', 'PRODUCTION_CONTROL'], intakeSources: ['reports', 'Hermes provenance', 'Knowledge Layer'], escalationTargets: ['Ray Review', 'Research Lead'], serviceLevelPolicy: { acknowledgementTargetMinutes: 60, reviewTargetHours: 24, resolutionTargetHours: 96 }, healthSource: 'Knowledge health summary', status: 'ACTIVE' },
  { departmentId: 'credit_funding', name: 'Credit and Funding', description: 'Credit-report processing, discrepancy workflows, readiness scoring, readiness-review journey, and client workflow blockers.', ownerRole: 'Credit Workflow Lead', executiveCoordinator: 'hermes', defaultOperationMode: 'DRAFT_ONLY', allowedCapabilityIds: ['hermes_customer_aggregate_tool', 'credit_workflow_engine', 'funding_readiness_reviews', 'revenue_activation_test_mode'], prohibitedCapabilityIds: ['external_dispute_submission', 'lender_application_submitter', 'stripe_live_activation'], allowedDataClasses: ['INTERNAL_METADATA', 'CLIENT_AGGREGATE'], prohibitedDataClasses: ['CLIENT_PII', 'CREDENTIALS', 'FINANCIAL_DATA', 'PRODUCTION_CONTROL'], intakeSources: ['client aggregate adapter', 'readiness review reports', 'credit workflow reports'], escalationTargets: ['Ray Review', 'Engineering Lead', 'Operations Coordinator'], serviceLevelPolicy: { acknowledgementTargetMinutes: 30, reviewTargetHours: 8, resolutionTargetHours: 72 }, healthSource: 'Credit workflow and readiness review reports', status: 'ACTIVE' },
];

export const syntheticDepartmentQueue: DepartmentQueueItem[] = [
  { itemId: 'ops-client-live-data-flag-verification', departmentId: 'operations', title: 'Client live-data flag verification', summary: 'Coordinate proof that client-facing live-data flags remain intentional and do not expose unverified records.', sourceType: 'synthetic_certification_seed', sourceId: 'wave4.synthetic.operations.1', priority: 'P1_CUSTOMER', urgency: 'HIGH', riskLevel: 'HIGH', operationMode: 'ADVISORY', status: 'TRIAGED', ownerRole: 'Operations Coordinator', assignedActorId: 'role:operations_coordinator', capabilityIds: ['executive_command_center', 'hermes_customer_aggregate_tool'], dependencyIds: ['eng-live-data-adapter-check'], blockerIds: ['blocker-client-live-data-dependency'], requiresApproval: false, evidenceIds: ['wave4.synthetic.operations', 'hermes_founder_acceptance_certification'], completionCriteria: ['Engineering evidence reviewed', 'No client PII exposed', 'Hermes status answer updated if evidence changes'], createdAt: hoursAgo(7), updatedAt: hoursAgo(1), dueAt: new Date(Date.now() + 20 * 60 * 60 * 1000).toISOString(), synthetic: true },
  { itemId: 'eng-provider-state-reconciliation', departmentId: 'engineering', title: 'Hermes provider-state reconciliation', summary: 'Keep provider state truthful while external model routing remains TEST_ONLY_EVIDENCE_CONFLICTED.', sourceType: 'synthetic_certification_seed', sourceId: 'wave4.synthetic.engineering.1', priority: 'P0_COMPANY', urgency: 'HIGH', riskLevel: 'HIGH', operationMode: 'DRAFT_ONLY', status: 'PLANNED', ownerRole: 'Engineering Lead', assignedActorId: 'role:engineering_lead', capabilityIds: ['hermes_provider_honesty', 'hermes_model_provider_profile'], dependencyIds: [], blockerIds: [], requiresApproval: true, approvalId: 'ray-review-provider-state', evidenceIds: ['nexus_3_hermes_founder_acceptance_status', 'capability_os_registry'], completionCriteria: ['Provider UI/report state matches TEST_ONLY_EVIDENCE_CONFLICTED', 'No provider keys exposed', 'No client PII sent externally'], createdAt: hoursAgo(5), updatedAt: hoursAgo(2), synthetic: true },
  { itemId: 'research-top-revenue-candidates', departmentId: 'research', title: 'Review top revenue research candidates', summary: 'Evaluate report-backed revenue opportunities and keep Alpha in public-research-only mode.', sourceType: 'synthetic_certification_seed', sourceId: 'wave4.synthetic.research.1', priority: 'P4_RESEARCH', urgency: 'MEDIUM', riskLevel: 'MEDIUM', operationMode: 'ADVISORY', status: 'NEW', ownerRole: 'Research Lead', assignedActorId: 'role:research_lead', capabilityIds: ['hermes_research_handoff', 'hermes_report_catalog_tool'], dependencyIds: ['knowledge-report-freshness-review'], blockerIds: [], requiresApproval: false, evidenceIds: ['repo_intelligence_registry', 'approved_report_catalog'], completionCriteria: ['Candidate evidence summarized', 'PII excluded', 'Ray Review prepared only if action is requested'], createdAt: hoursAgo(3), updatedAt: hoursAgo(3), synthetic: true },
  { itemId: 'knowledge-refresh-hermes-report-evidence', departmentId: 'knowledge', title: 'Refresh stale Hermes report evidence', summary: 'Confirm Hermes reports, provenance labels, and capability registry references are current after Founder Acceptance.', sourceType: 'synthetic_certification_seed', sourceId: 'wave4.synthetic.knowledge.1', priority: 'P3_OPERATIONS', urgency: 'MEDIUM', riskLevel: 'MEDIUM', operationMode: 'READ_ONLY', status: 'VERIFYING', ownerRole: 'Knowledge Steward', assignedActorId: 'role:knowledge_steward', capabilityIds: ['hermes_report_catalog_tool', 'hermes_provenance_tool'], dependencyIds: [], blockerIds: [], requiresApproval: false, evidenceIds: ['nexus_3_wave_4a_5_live_founder_acceptance', 'report_catalog'], completionCriteria: ['Report catalog can list Founder Acceptance evidence', 'Provenance answers cite prior response evidence'], createdAt: hoursAgo(10), updatedAt: hoursAgo(1), synthetic: true },
  { itemId: 'credit-define-readiness-review-deliverable', departmentId: 'credit_funding', title: 'Define $97 readiness-review deliverable', summary: 'Specify what the customer receives, intake requirements, review timeline, and post-payment workflow while Stripe remains test-only.', sourceType: 'synthetic_certification_seed', sourceId: 'wave4.synthetic.credit.1', priority: 'P2_REVENUE', urgency: 'HIGH', riskLevel: 'HIGH', operationMode: 'DRAFT_ONLY', status: 'BLOCKED', ownerRole: 'Credit Workflow Lead', assignedActorId: 'role:credit_workflow_lead', capabilityIds: ['revenue_activation_test_mode', 'funding_readiness_reviews'], dependencyIds: ['eng-live-data-adapter-check'], blockerIds: ['blocker-readiness-deliverable-approval'], requiresApproval: true, approvalId: 'ray-review-readiness-deliverable', evidenceIds: ['readiness_review_operating_context', 'stripe_test_mode_policy'], completionCriteria: ['Deliverable is not a funding guarantee', 'Client-facing copy is Ray-reviewed', 'Stripe remains test-only'], createdAt: hoursAgo(9), updatedAt: hoursAgo(2), dueAt: new Date(Date.now() + 28 * 60 * 60 * 1000).toISOString(), synthetic: true },
];

export const syntheticDepartmentBlockers: DepartmentBlocker[] = [
  { blockerId: 'blocker-client-live-data-dependency', departmentId: 'operations', title: 'Engineering adapter evidence required', description: 'Operations cannot close client live-data verification until Engineering confirms adapter and UI behavior.', blockerType: 'DEPENDENCY', severity: 'HIGH', status: 'OPEN', affectedItemIds: ['ops-client-live-data-flag-verification', 'credit-define-readiness-review-deliverable'], ownerRole: 'Engineering Lead', mitigation: 'Run authenticated synthetic admin/client proof and attach result.', evidenceIds: ['hermes_founder_acceptance_certification'], createdAt: hoursAgo(6) },
  { blockerId: 'blocker-readiness-deliverable-approval', departmentId: 'credit_funding', title: 'Ray approval required for client-facing readiness deliverable', description: 'The $97 deliverable cannot become client-facing until Ray reviews exact promise, disclaimers, and workflow.', blockerType: 'APPROVAL', severity: 'HIGH', status: 'OPEN', affectedItemIds: ['credit-define-readiness-review-deliverable'], ownerRole: 'Ray Review', mitigation: 'Ray Review decision after Ray explicitly asks for an approval draft.', evidenceIds: ['stripe_test_mode_policy', 'readiness_review_operating_context'], createdAt: hoursAgo(8) },
];

export const syntheticDepartmentIncidents: DepartmentIncident[] = [
  { incidentId: 'incident-none-active-wave4', departmentId: 'operations', title: 'No active production incident in Wave 4 seed', status: 'CLOSED', impact: 'No active incident asserted from synthetic seed.', affectedSystems: ['department_operations'], currentState: 'Closed placeholder used to certify incident workflow shape.', containment: 'No containment required.', ownerRole: 'Operations Coordinator', nextAction: 'Open a real incident only from observed production evidence.', evidenceIds: ['wave4.synthetic.incident.contract'], verification: 'Incident closure requires evidence; this seed is explicitly synthetic.', createdAt: hoursAgo(1), updatedAt: hoursAgo(1) },
];

export const syntheticWorkVerifications: WorkVerification[] = [
  { verificationId: 'verify-knowledge-report-evidence', queueItemId: 'knowledge-refresh-hermes-report-evidence', criteriaResults: [
    { criterion: 'Report catalog can list Founder Acceptance evidence', passed: true, evidenceIds: ['nexus_3_wave_4a_5_live_founder_acceptance'] },
    { criterion: 'Provenance answers cite prior response evidence', passed: true, evidenceIds: ['hermes_provenance_tool'] },
  ], verifiedBy: 'Knowledge Steward', verifiedAt: hoursAgo(1), result: 'PASS', notes: 'Synthetic verification for Wave 4 contract; no customer data used.' },
];

export const syntheticExecutionPlans: GovernedExecutionPlan[] = [
  { executionId: 'execution-plan-status-refresh-demo', queueItemId: 'ops-client-live-data-flag-verification', capabilityId: 'executive_command_center', operationMode: 'BOUNDED_EXECUTION', approvedScope: ['read authenticated admin status', 'capture sanitized evidence'], prohibitedScope: ['client PII', 'external messages', 'live payment activation'], maximumOperations: 3, timeLimitMinutes: 10, preconditions: ['Ray approval recorded if any write is required', 'Synthetic account only'], completionCriteria: ['Evidence attached', 'No unresolved critical blocker'], rollbackPlan: ['No write operation allowed in this plan'], approvalId: 'read-only-no-write', approvedBy: 'policy:read_only', approvedAt: hoursAgo(1), status: 'READY', evidenceIds: ['capability_os_registry'] },
];

function priorityRank(priority: QueuePriority): number { return { P0_COMPANY: 0, P1_CUSTOMER: 1, P2_REVENUE: 2, P3_OPERATIONS: 3, P4_RESEARCH: 4 }[priority]; }
function severityRank(severity: Severity): number { return { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }[severity]; }

export function sortQueueByPriority(items: DepartmentQueueItem[]): DepartmentQueueItem[] {
  return [...items].sort((a, b) => priorityRank(a.priority) - priorityRank(b.priority) || severityRank(a.riskLevel) - severityRank(b.riskLevel) || String(a.dueAt || '').localeCompare(String(b.dueAt || '')));
}

export function canCompleteQueueItem(item: DepartmentQueueItem, verifications: WorkVerification[] = syntheticWorkVerifications, blockers: DepartmentBlocker[] = syntheticDepartmentBlockers): boolean {
  const openCriticalBlocker = blockers.some((blocker) => item.blockerIds.includes(blocker.blockerId) && blocker.status === 'OPEN' && ['CRITICAL', 'HIGH'].includes(blocker.severity));
  const verification = verifications.find((entry) => entry.queueItemId === item.itemId);
  return Boolean(verification && verification.result === 'PASS' && !openCriticalBlocker && item.completionCriteria.every((criterion) => verification.criteriaResults.some((result) => result.criterion === criterion && result.passed)));
}

export function buildDepartmentHealth(departmentId: string, observedAt = now()): DepartmentHealth {
  const items = syntheticDepartmentQueue.filter((item) => item.departmentId === departmentId);
  const blockers = syntheticDepartmentBlockers.filter((blocker) => blocker.departmentId === departmentId || blocker.affectedItemIds.some((id) => items.some((item) => item.itemId === id)));
  const open = items.filter((item) => !['COMPLETE', 'CANCELLED'].includes(item.status));
  const blocked = items.filter((item) => item.status === 'BLOCKED' || item.blockerIds.some((id) => syntheticDepartmentBlockers.some((blocker) => blocker.blockerId === id && blocker.status === 'OPEN')));
  const awaitingApproval = items.filter((item) => item.status === 'AWAITING_APPROVAL' || item.requiresApproval).length;
  const overdue = items.filter((item) => item.dueAt && new Date(item.dueAt).getTime() < Date.now()).length;
  const oldest = open.length ? Math.round(Math.max(...open.map((item) => (Date.now() - new Date(item.createdAt).getTime()) / 36e5))) : 0;
  const complete = items.filter((item) => item.status === 'COMPLETE').length;
  const state: DepartmentHealth['state'] = blocked.some((item) => item.riskLevel === 'CRITICAL') ? 'BLOCKED' : blocked.length ? 'DEGRADED' : 'HEALTHY';
  return { departmentId, state, openItems: open.length, criticalItems: items.filter((item) => item.riskLevel === 'CRITICAL').length, blockedItems: blocked.length, awaitingApproval, overdueItems: overdue, oldestOpenItemAgeHours: oldest, completionRate: items.length ? Math.round((complete / items.length) * 100) : 100, topRisks: sortQueueByPriority(items).filter((item) => ['HIGH', 'CRITICAL'].includes(item.riskLevel)).map((item) => item.title).slice(0, 3), topBlockers: blockers.filter((blocker) => blocker.status === 'OPEN').map((blocker) => blocker.title).slice(0, 3), observedAt };
}

export function getDepartmentOperationsSnapshot(): DepartmentOperationsSnapshot {
  const generatedAt = now();
  return { generatedAt, departments: activeDepartmentRegistry, queueItems: sortQueueByPriority(syntheticDepartmentQueue), blockers: syntheticDepartmentBlockers, incidents: syntheticDepartmentIncidents, verifications: syntheticWorkVerifications, executionPlans: syntheticExecutionPlans, health: activeDepartmentRegistry.map((department) => buildDepartmentHealth(department.departmentId, generatedAt)), evidenceIds: ['wave4.department_registry', 'wave4.synthetic_department_queue', 'capability_os_registry', 'ray_review_reuse_contract'], limitations: ['Synthetic certification seed only; no real customer PII is included.', 'Durable tables are additive and admin-only; live queue writes remain governed.', 'Draft tools prepare conversation actions only unless Ray Review records approval.'] };
}

export function departmentByQuery(query: string): NexusDepartmentDefinition | null {
  const lower = query.toLowerCase().replace(/and funding/g, 'funding');
  return activeDepartmentRegistry.find((department) => lower.includes(department.departmentId.replace('_', ' ')) || lower.includes(department.name.toLowerCase()) || (department.departmentId === 'credit_funding' && /credit|funding/.test(lower))) || null;
}

export function getDepartmentQueue(departmentId?: string): DepartmentQueueItem[] { return sortQueueByPriority(departmentId ? syntheticDepartmentQueue.filter((item) => item.departmentId === departmentId) : syntheticDepartmentQueue); }

export function getTopDepartmentRisk(): { department: NexusDepartmentDefinition; health: DepartmentHealth; item?: DepartmentQueueItem } {
  const snapshot = getDepartmentOperationsSnapshot();
  const item = sortQueueByPriority(snapshot.queueItems)[0];
  const department = snapshot.departments.find((entry) => entry.departmentId === item.departmentId) || snapshot.departments[0];
  const health = snapshot.health.find((entry) => entry.departmentId === department.departmentId) || buildDepartmentHealth(department.departmentId);
  return { department, health, item };
}

export function prepareDepartmentTaskDraft(query: string): string {
  const snapshot = getDepartmentOperationsSnapshot();
  const target = departmentByQuery(query);
  const item = target ? getDepartmentQueue(target.departmentId)[0] : snapshot.queueItems.find((queueItem) => queueItem.status === 'BLOCKED') || snapshot.queueItems[0];
  const preflight = runCapabilityPreflight(item.capabilityIds[0] || 'hermes_work_summary_tool', { actorRole: 'admin', environment: 'production', requestedAction: 'propose', requestedDataClasses: ['INTERNAL_METADATA'], costWithinLimit: true });
  return 'Governed task draft for **' + item.title + '** (' + item.departmentId + '). Mode: ' + item.operationMode + '. Priority: ' + item.priority + '; risk: ' + item.riskLevel + '. First step: ' + (item.completionCriteria[0] || 'attach evidence and verify completion criteria') + '. Capability preflight: ' + (preflight.allowed ? 'passed for draft/propose' : preflight.decision) + '. This is conversation-only and draft-only: nothing has been saved, assigned, submitted, approved, executed, sent, or charged. It requires the governed review path before any action runs.';
}

export function prepareDepartmentRayReviewDraft(query: string): string {
  const item = getDepartmentQueue().find((queueItem) => queueItem.requiresApproval && /first step|top|blocked|that|it|engineering|credit|funding/i.test(query)) || getDepartmentQueue()[0];
  return 'Ray Review draft prepared for **' + item.title + '**. Decision requested: approve, reject, or request changes to the bounded plan. Risk: ' + item.riskLevel + '. Affected capability: ' + (item.capabilityIds[0] || 'department_operations') + '. Evidence: ' + item.evidenceIds.join(', ') + '. This is conversation-only: nothing has been saved, approved, or executed. It requires Ray Review; Hermes cannot approve this or run it.';
}

export function formatDepartmentList(): string {
  const snapshot = getDepartmentOperationsSnapshot();
  return 'Department Operations is active for ' + snapshot.departments.length + ' governed departments: ' + snapshot.departments.map((department) => department.name).join(', ') + '. All departments use operation modes, Capability OS preflight, Ray Review for approvals, evidence-backed completion, and synthetic certification data only in this seed.';
}

export function formatDepartmentStatus(query = ''): string {
  const snapshot = getDepartmentOperationsSnapshot();
  const target = departmentByQuery(query);
  if (target) {
    const health = snapshot.health.find((entry) => entry.departmentId === target.departmentId) || buildDepartmentHealth(target.departmentId);
    const queue = getDepartmentQueue(target.departmentId);
    return target.name + ' is ' + health.state + '. Open items: ' + health.openItems + '; blocked: ' + health.blockedItems + '; awaiting approval: ' + health.awaitingApproval + '; overdue: ' + health.overdueItems + '. Top work: ' + (queue[0]?.title || 'none') + '. Owner role: ' + target.ownerRole + '. Evidence: department registry and synthetic queue seed.';
  }
  const risk = getTopDepartmentRisk();
  return 'Department Operations is ACTIVE with ' + snapshot.departments.length + ' departments and ' + snapshot.queueItems.length + ' synthetic queue items. Highest current risk is ' + risk.department.name + ': ' + risk.item?.title + ' (' + risk.item?.priority + ', ' + risk.item?.riskLevel + ') because it affects ' + risk.item?.summary + '.';
}

export function formatDepartmentQueue(query = ''): string {
  const target = departmentByQuery(query);
  const queue = getDepartmentQueue(target?.departmentId);
  const label = target?.name || 'all active departments';
  return label + ' queue (' + queue.length + ' item' + (queue.length === 1 ? '' : 's') + '):\n' + queue.map((item) => '- ' + item.title + ': ' + item.status + ', ' + item.priority + ', ' + item.operationMode + ', owner ' + (item.ownerRole || 'unassigned') + ', approval ' + (item.requiresApproval ? 'required' : 'not required')).join('\n');
}

export function formatDepartmentBlockers(query = ''): string {
  const target = departmentByQuery(query);
  const items = target ? syntheticDepartmentBlockers.filter((blocker) => blocker.departmentId === target.departmentId || blocker.affectedItemIds.some((id) => getDepartmentQueue(target.departmentId).some((item) => item.itemId === id))) : syntheticDepartmentBlockers;
  if (!items.length) return (target?.name || 'Department Operations') + ' has no open blockers in the synthetic Wave 4 queue.';
  return 'Open blockers for ' + (target?.name || 'Department Operations') + ':\n' + items.map((blocker) => '- ' + blocker.title + ': ' + blocker.blockerType + ', ' + blocker.severity + ', owner ' + (blocker.ownerRole || 'unassigned') + '. Unblock by: ' + (blocker.mitigation || 'record mitigation evidence')).join('\n');
}

export function formatDepartmentApprovals(query = ''): string {
  const target = departmentByQuery(query);
  const queue = getDepartmentQueue(target?.departmentId).filter((item) => item.requiresApproval);
  if (!queue.length) return (target?.name || 'Department Operations') + ' has no approval-required queue item in the synthetic Wave 4 seed.';
  return 'Approval-required department work:\n' + queue.map((item) => '- ' + item.title + ': ' + (item.approvalId || 'Ray Review required') + ', risk ' + item.riskLevel + ', requested approver Ray Davis.').join('\n');
}

export function formatDepartmentCompletedWork(): string {
  const completed = syntheticDepartmentQueue.filter((item) => item.status === 'COMPLETE' || canCompleteQueueItem(item));
  if (!completed.length) return 'No department queue item is marked COMPLETE. Knowledge verification has PASS evidence but remains VERIFYING until the queue status is explicitly advanced.';
  return 'Recently completed department work:\n' + completed.map((item) => '- ' + item.title + ': evidence ' + item.evidenceIds.join(', ')).join('\n');
}

export function formatDepartmentIncidents(): string {
  return 'Department incidents:\n' + syntheticDepartmentIncidents.map((incident) => '- ' + incident.title + ': ' + incident.status + '; impact ' + incident.impact + '; owner ' + incident.ownerRole + '; verification ' + incident.verification).join('\n');
}

export function formatDepartmentDependencies(): string {
  const deps = syntheticDepartmentQueue.filter((item) => item.dependencyIds.length || item.blockerIds.length);
  return 'Cross-department dependencies:\n' + deps.map((item) => '- ' + item.title + ': dependencies ' + (item.dependencyIds.join(', ') || 'none') + '; blockers ' + (item.blockerIds.join(', ') || 'none')).join('\n');
}
