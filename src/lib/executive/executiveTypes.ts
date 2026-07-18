export type EvidenceState = 'LIVE' | 'CACHED' | 'REPORT_BACKED' | 'MOCK' | 'UNKNOWN' | 'BLOCKED' | 'DEFERRED';
export type Freshness = 'CURRENT' | 'STALE' | 'UNKNOWN';
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';

export interface ExecutiveEvidence {
  state: EvidenceState;
  source: string;
  observedAt?: string;
  freshness: Freshness;
  confidence: Confidence;
}

export interface ExecutiveMetric {
  id: string;
  label: string;
  value: string | number;
  status: string;
  priority: 'P0' | 'P1' | 'P2' | 'P3' | 'P4';
  evidence: ExecutiveEvidence;
}

export interface ExecutiveActionItem {
  id: string;
  title: string;
  reason: string;
  priority: 'P0' | 'P1' | 'P2' | 'P3' | 'P4';
  status: string;
  route: string;
  evidence: ExecutiveEvidence;
}

export interface ExecutiveApprovalItem {
  id: string;
  type: string;
  source: string;
  proposer: string;
  department: string;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'UNKNOWN';
  summary: string;
  evidence: ExecutiveEvidence;
  financialEffect: string;
  customerEffect: string;
  privacyEffect: string;
  deadline: string;
  state: 'PENDING' | 'APPROVED' | 'REJECTED' | 'REVISION_REQUESTED' | 'DEFERRED' | 'EXPIRED' | 'BLOCKED';
  requiredApprover: string;
  linkedTaskRequest: string | null;
  linkedAgentJob: string | null;
  linkedEventHistory: string[];
}

export interface GovernedWorkItem {
  id: string;
  title: string;
  department: string;
  assignee: string;
  lifecycle: 'DRAFT' | 'AWAITING_APPROVAL' | 'APPROVED' | 'QUEUED' | 'RUNNING' | 'BLOCKED' | 'NEEDS_REVIEW' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'DEFERRED';
  approvalState: string;
  executionStatus: string;
  blocker: string;
  nextAction: string;
  evidence: ExecutiveEvidence;
}

export interface DepartmentStatus {
  departmentId: string;
  displayName: string;
  purpose: string;
  currentStatus: 'ACTIVE' | 'PARTIAL' | 'PLANNED' | 'BLOCKED' | 'PAUSED' | 'NOT_CONFIGURED';
  owner: string;
  activeCapabilities: string[];
  activeGovernedWork: number;
  pendingApprovals: number;
  blockers: string[];
  kpis: string[];
  activationState: string;
  evidence: ExecutiveEvidence;
}

export interface ExecutiveHealthItem {
  component: string;
  category: string;
  status: 'HEALTHY' | 'DEGRADED' | 'BLOCKED' | 'NOT_CONFIGURED' | 'DEFERRED' | 'UNKNOWN' | 'STALE' | 'BLOCKED_BY_POLICY' | 'PROHIBITED';
  source: string;
  impact: string;
  owner: string;
  recommendedAction: string;
  evidence: ExecutiveEvidence;
}

export interface RepoIntelligenceItem {
  candidateId: string;
  repository: string;
  category: string;
  license: string;
  maintenanceStatus: string;
  securityStatus: string;
  nexusOverlap: string[];
  candidateStatus: string;
  proposedDisposition: string;
  blueprintWave: string;
  decisionRequired: string;
  evidenceLinks: string[];
  accessProfile?: string;
}

export interface ExecutiveBrief {
  generatedAt: string;
  sections: Array<{
    id: string;
    title: string;
    facts: string[];
    interpretations: string[];
    recommendations: string[];
    unknowns: string[];
    blockedData: string[];
  }>;
}

export interface ExecutiveCommandCenterState {
  generatedAt: string;
  phoenixDateTime: string;
  metrics: ExecutiveMetric[];
  topActions: ExecutiveActionItem[];
  approvals: ExecutiveApprovalItem[];
  governedWork: GovernedWorkItem[];
  departments: DepartmentStatus[];
  customerSummary: ExecutiveMetric[];
  revenueSummary: ExecutiveMetric[];
  systemHealth: ExecutiveHealthItem[];
  repoIntelligence: RepoIntelligenceItem[];
  capabilityOS?: {
    total: number;
    byActivationMode: Record<string, number>;
    byHealth: Record<string, number>;
    approvalGated: number;
    awaitingRayApproval: number;
    missingCredentials: number;
    dependencyBlocked: number;
    proposals: number;
    topCapabilities: Array<{
      capabilityId: string;
      name: string;
      departmentId: string;
      activationMode: string;
      approvalLevel: string;
      healthStatus: string;
      credentialRequirements: string[];
      dependencies: string[];
      rayApprovalState: string;
    }>;
  };
  knowledgeHealth?: {
    totalRecords: number;
    approvedKnowledge: number;
    unverifiedClaims: number;
    staleRecords: number;
    expiredRecords: number;
    conflicts: number;
    missingProvenance: number;
    pendingReviews: number;
    rejectedFindings: number;
    recordsBlockedByPolicy: number;
    alphaSubmissionsAwaitingReview: number;
    clientSafeKnowledge: number;
    brainProfiles: number;
    activeBrains: number;
    plannedDepartmentTemplates: number;
    retrievalDenials: number;
    documentEvidenceStatus: string;
    evaluationPassed: number;
    evaluationTotal: number;
  };
  brainProfiles?: Array<{
    brainId: string;
    name: string;
    role: string;
    status: string;
    departmentId?: string;
    mayUseSupabase: boolean;
    mayUseWeb: boolean;
    mayAccessClientPii: boolean;
    mayApproveKnowledge: boolean;
    mayExecuteWork: boolean;
    requiredApprovalLevel: string;
    allowedCapabilities: string[];
    prohibitedDataClasses: string[];
  }>;
  dailyBrief: ExecutiveBrief;
  limitations: string[];
}
