import type { EvidenceState } from '../executive/executiveTypes';

export type CapabilityType =
  | 'INTERNAL_SERVICE'
  | 'SUPABASE_WORKFLOW'
  | 'CONNECTOR'
  | 'MODEL_PROVIDER'
  | 'MCP_SERVER'
  | 'RESEARCH_TOOL'
  | 'AUTOMATION'
  | 'DOCUMENT_PROCESSOR'
  | 'PAYMENT'
  | 'COMMUNICATION'
  | 'DEPLOYMENT'
  | 'ANALYTICS'
  | 'TRADING_RESEARCH'
  | 'CLIENT_FEATURE'
  | 'ADMIN_FEATURE'
  | 'EXECUTIVE_FEATURE'
  | 'OTHER';

export type CapabilityActivationMode =
  | 'ACTIVE'
  | 'READ_ONLY'
  | 'APPROVAL_GATED'
  | 'TEST_ONLY'
  | 'MOCK'
  | 'NOT_CONFIGURED'
  | 'DEFERRED'
  | 'BLOCKED_BY_POLICY'
  | 'PROHIBITED'
  | 'RETIRED';

export type CapabilityApprovalLevel = 'NONE' | 'OPERATOR' | 'ADMIN' | 'RAY_REVIEW' | 'RAY_EXPLICIT' | 'LEGAL_AND_RAY';
export type CapabilitySecurityClass = 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED' | 'HIGH_RISK';
export type CapabilityDataClass =
  | 'PUBLIC_DATA'
  | 'INTERNAL_METADATA'
  | 'CLIENT_AGGREGATE'
  | 'CLIENT_PII'
  | 'FINANCIAL_DATA'
  | 'CREDENTIALS'
  | 'SOURCE_CODE'
  | 'PRODUCTION_CONTROL'
  | 'NONE';
export type CapabilityHealthStatus = 'HEALTHY' | 'DEGRADED' | 'BLOCKED' | 'NOT_CONFIGURED' | 'DEFERRED' | 'UNKNOWN' | 'STALE' | 'PROHIBITED';
export type CapabilitySourceType = 'NEXUS_NATIVE' | 'EXTERNAL_SERVICE' | 'OPEN_SOURCE_DEPENDENCY' | 'MCP' | 'API' | 'REPORT_BACKED' | 'CONFIG_BACKED' | 'UNKNOWN';
export type RayApprovalState = 'NOT_REQUIRED' | 'PENDING' | 'APPROVED' | 'REJECTED' | 'DEFERRED';

export interface CapabilityEvidence {
  source: string;
  state: EvidenceState;
  observedAt?: string;
}

export interface NexusCapability {
  capabilityId: string;
  name: string;
  description: string;
  capabilityType: CapabilityType;
  departmentId: string;
  supportingDepartments?: string[];
  ownerType: 'HUMAN' | 'DEPARTMENT' | 'SYSTEM' | 'UNASSIGNED';
  ownerId?: string;
  sourceType: CapabilitySourceType;
  activationMode: CapabilityActivationMode;
  approvalLevel: CapabilityApprovalLevel;
  securityClass: CapabilitySecurityClass;
  allowedDataClasses: CapabilityDataClass[];
  prohibitedDataClasses: CapabilityDataClass[];
  permissions: string[];
  credentialRequirements: string[];
  dependencies: string[];
  costModel: 'FREE' | 'USAGE_BASED' | 'SUBSCRIPTION' | 'SELF_HOSTED' | 'INTERNAL' | 'UNKNOWN';
  estimatedMonthlyCost?: number | null;
  costNotes?: string;
  healthSource: string;
  healthStatus: CapabilityHealthStatus;
  healthFreshness?: string;
  lastVerifiedAt?: string;
  eventsConsumed: string[];
  eventsEmitted: string[];
  tests: string[];
  rollbackPlan: string;
  disablePlan: string;
  maintenanceOwner?: string;
  hermesMayRecommend: boolean;
  hermesMayExecute: boolean;
  alphaMayUse: boolean;
  clientAiMayUse: boolean;
  rayApprovalState: RayApprovalState;
  evidence: CapabilityEvidence[];
  supersedes?: string[];
  supersededBy?: string;
  notes?: string;
}

export interface CredentialRequirement {
  credentialId: string;
  required: boolean;
  environment: 'browser' | 'server' | 'edge_function' | 'local_operator' | 'external_host' | 'none';
  readiness: 'CONFIGURED' | 'MISSING' | 'DEFERRED' | 'PROHIBITED' | 'UNKNOWN' | 'NOT_REQUIRED';
  owner: string;
  rotationRequirement: string;
  secretLocationCategory: string;
}

export interface CapabilityProposal {
  proposalId: string;
  candidateName: string;
  sourceRepository?: string;
  sourceType: string;
  proposedCapabilityType: CapabilityType;
  proposedDepartment: string;
  businessProblem: string;
  proposedValue: string;
  existingNexusOverlap: string[];
  licenseStatus: 'VERIFIED' | 'UNKNOWN' | 'CONDITIONAL' | 'INCOMPATIBLE';
  securityStatus: 'REVIEWED' | 'PARTIAL' | 'UNKNOWN' | 'REJECTED';
  proposedDisposition:
    | 'INTEGRATE_AS_DEPENDENCY'
    | 'ADAPT_PERMITTED_CODE'
    | 'STUDY_ARCHITECTURE_OR_WORKFLOW_ONLY'
    | 'REPLACE_WITH_EXISTING_NEXUS_CAPABILITY'
    | 'DEFER'
    | 'REJECT'
    | 'INTEGRATE_AS_CONTROLLED_EXTERNAL_TOOL';
  requestedActivationMode: CapabilityActivationMode;
  estimatedCost: string;
  dataRisk: string;
  dependencies: string[];
  evidence: string[];
  status: 'DRAFT' | 'AWAITING_REVIEW' | 'APPROVED_FOR_EVALUATION' | 'REJECTED' | 'DEFERRED' | 'APPROVED_FOR_IMPLEMENTATION';
  rayDecisionRequired: boolean;
}

export interface CapabilityPolicyContext {
  actorRole: 'ray' | 'admin' | 'operator' | 'agent' | 'client' | 'alpha' | 'client_ai' | 'unknown';
  environment: 'development' | 'test' | 'production' | 'unknown';
  requestedAction: 'read' | 'recommend' | 'execute' | 'activate' | 'write' | 'install' | 'disable' | 'propose';
  requestedDataClasses?: CapabilityDataClass[];
  approvalState?: RayApprovalState;
  credentialReadiness?: Record<string, CredentialRequirement['readiness']>;
  dependencyHealth?: Record<string, CapabilityHealthStatus>;
  costWithinLimit?: boolean;
}

export interface CapabilityPolicyDecision {
  allowed: boolean;
  decision:
    | 'ALLOW'
    | 'DENY'
    | 'REQUIRES_APPROVAL'
    | 'NOT_CONFIGURED'
    | 'BLOCKED_BY_POLICY'
    | 'PROHIBITED'
    | 'DEPENDENCY_UNHEALTHY'
    | 'CREDENTIAL_MISSING'
    | 'DATA_CLASS_NOT_ALLOWED'
    | 'COST_LIMIT_EXCEEDED'
    | 'UNKNOWN_CAPABILITY';
  reasons: string[];
  requiredApprovalLevel?: CapabilityApprovalLevel;
  missingDependencies?: string[];
  missingCredentials?: string[];
}

export interface CapabilityPreflightResult extends CapabilityPolicyDecision {
  capabilityId: string;
  event: {
    action:
      | 'CAPABILITY_PREFLIGHT_PASSED'
      | 'CAPABILITY_PREFLIGHT_DENIED'
      | 'CAPABILITY_APPROVAL_REQUIRED'
      | 'CAPABILITY_DEPENDENCY_BLOCKED'
      | 'CAPABILITY_CREDENTIAL_MISSING'
      | 'CAPABILITY_DATA_POLICY_DENIED'
      | 'CAPABILITY_COST_POLICY_DENIED'
      | 'CAPABILITY_DISABLED';
    capabilityId: string;
    summary: string;
    sanitized: true;
  };
}

export interface CapabilityOSSummary {
  generatedAt: string;
  total: number;
  byActivationMode: Record<string, number>;
  byHealth: Record<string, number>;
  approvalGated: number;
  awaitingRayApproval: number;
  missingCredentials: number;
  dependencyBlocked: number;
  proposals: CapabilityProposal[];
  capabilities: NexusCapability[];
}
