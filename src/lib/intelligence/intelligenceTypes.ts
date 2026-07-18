export type IntelligenceRecordType =
  | 'SOURCE'
  | 'EVIDENCE'
  | 'CLAIM'
  | 'OBSERVATION'
  | 'APPROVED_KNOWLEDGE'
  | 'POLICY'
  | 'RECOMMENDATION'
  | 'MEMORY'
  | 'CONTEXT'
  | 'MODEL_OUTPUT';

export type IntelligenceApprovalState =
  | 'DRAFT'
  | 'UNVERIFIED'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'SUPERSEDED'
  | 'EXPIRED'
  | 'DEFERRED';

export type IntelligenceFreshness = 'CURRENT' | 'AGING' | 'STALE' | 'EXPIRED' | 'UNKNOWN';
export type IntelligenceConfidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';

export type IntelligenceSourceType =
  | 'SUPABASE'
  | 'USER_INPUT'
  | 'CLIENT_DOCUMENT'
  | 'INTERNAL_REPORT'
  | 'PUBLIC_WEB'
  | 'GITHUB'
  | 'RESEARCH_AGENT'
  | 'MODEL_OUTPUT'
  | 'POLICY_FILE'
  | 'CONFIG'
  | 'SYSTEM_EVENT'
  | 'UNKNOWN';

export type IntelligenceDataClass =
  | 'PUBLIC'
  | 'INTERNAL'
  | 'EXECUTIVE'
  | 'CLIENT_AGGREGATE'
  | 'CLIENT_PII'
  | 'FINANCIAL'
  | 'CREDENTIAL'
  | 'SOURCE_CODE'
  | 'PRODUCTION_CONTROL';

export type IntelligenceEvidenceState = 'LIVE' | 'CACHED' | 'REPORT_BACKED' | 'MOCK' | 'UNKNOWN' | 'BLOCKED' | 'DEFERRED';

export interface NexusIntelligenceRecord {
  recordId: string;
  recordType: IntelligenceRecordType;
  title: string;
  summary: string;
  content?: string;
  domain: string;
  departmentId?: string;
  tenantId?: string | null;
  clientId?: string | null;
  sourceType: IntelligenceSourceType;
  sourceId?: string;
  sourceUri?: string;
  sourceTitle?: string;
  sourceAuthor?: string;
  sourceObservedAt?: string;
  approvalState: IntelligenceApprovalState;
  approvedBy?: string;
  approvedAt?: string;
  confidence: IntelligenceConfidence;
  freshness: IntelligenceFreshness;
  expiresAt?: string;
  dataClass: IntelligenceDataClass;
  allowedBrainIds: string[];
  prohibitedBrainIds: string[];
  parentRecordIds: string[];
  supportingEvidenceIds: string[];
  conflictingRecordIds: string[];
  supersedesRecordIds: string[];
  supersededBy?: string;
  policyIds: string[];
  capabilityIds: string[];
  createdAt: string;
  updatedAt: string;
  evidenceState: IntelligenceEvidenceState;
  notes?: string;
}

export type BrainContextDenialReason =
  | 'BRAIN_NOT_FOUND'
  | 'BRAIN_BLOCKED'
  | 'ACTOR_UNAUTHORIZED'
  | 'TENANT_MISMATCH'
  | 'RECORD_TYPE_PROHIBITED'
  | 'DOMAIN_PROHIBITED'
  | 'DATA_CLASS_PROHIBITED'
  | 'KNOWLEDGE_NOT_APPROVED'
  | 'KNOWLEDGE_STALE'
  | 'RECORD_SUPERSEDED'
  | 'CAPABILITY_NOT_ALLOWED'
  | 'POLICY_BLOCKED'
  | 'MISSING_PROVENANCE';

export interface BrainContextRequest {
  brainId: string;
  actorId?: string;
  actorRole: string;
  tenantId?: string;
  clientId?: string;
  query: string;
  requestedDomains?: string[];
  requestedDataClasses?: IntelligenceDataClass[];
  requestedCapabilities?: string[];
}

export interface BrainContextPackage {
  brainId: string;
  query: string;
  approvedKnowledge: NexusIntelligenceRecord[];
  evidence: NexusIntelligenceRecord[];
  observations: NexusIntelligenceRecord[];
  memories: Array<{
    memoryType: string;
    summary: string;
    sourceId?: string;
  }>;
  excluded: Array<{
    recordId?: string;
    reason: string;
  }>;
  facts: string[];
  policies: string[];
  recommendations: string[];
  unknowns: string[];
  conflicts: string[];
  freshnessSummary: string;
  evidenceState: IntelligenceEvidenceState;
  generatedAt: string;
}

export interface StructuredIntelligenceResult<T> {
  success: boolean;
  data?: T;
  errors: Array<{
    path?: string;
    code: string;
    message: string;
  }>;
  attempts: number;
  sourceModel?: string;
  evidenceIds: string[];
}
