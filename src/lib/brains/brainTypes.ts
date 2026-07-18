import type { IntelligenceDataClass, IntelligenceRecordType } from '../intelligence/intelligenceTypes';

export type BrainRole = 'HERMES' | 'ALPHA' | 'CLIENT_AI' | 'DEPARTMENT_AI';

export type BrainStatus = 'ACTIVE' | 'PARTIAL' | 'PLANNED' | 'BLOCKED' | 'PROHIBITED';

export type BrainMemoryType =
  | 'CONVERSATION_MEMORY'
  | 'SELECTION_MEMORY'
  | 'ADVISORY_MEMORY'
  | 'TASK_MEMORY'
  | 'EXECUTIVE_DECISION_MEMORY'
  | 'CLIENT_JOURNEY_MEMORY'
  | 'RESEARCH_MEMORY'
  | 'DEPARTMENT_WORK_MEMORY';

export interface AiBrainProfile {
  brainId: string;
  name: string;
  role: BrainRole;
  description: string;
  departmentId?: string;
  allowedKnowledgeDomains: string[];
  prohibitedKnowledgeDomains: string[];
  allowedDataClasses: IntelligenceDataClass[];
  prohibitedDataClasses: IntelligenceDataClass[];
  allowedRecordTypes: IntelligenceRecordType[];
  prohibitedRecordTypes: IntelligenceRecordType[];
  allowedMemoryTypes: BrainMemoryType[];
  allowedCapabilities: string[];
  mayUseWeb: boolean;
  mayUseSupabase: boolean;
  mayAccessClientPii: boolean;
  mayAccessPrivateSourceCode: boolean;
  mayCreateClaims: boolean;
  mayApproveKnowledge: boolean;
  mayCreateWork: boolean;
  mayExecuteWork: boolean;
  requiredApprovalLevel: string;
  contextBuilderId: string;
  retrievalPolicyId: string;
  memoryPolicyId: string;
  systemPolicyId: string;
  tenantIsolationRequired: boolean;
  evidenceRequired: boolean;
  citationsRequired: boolean;
  status: BrainStatus;
}

export interface BrainMemoryPolicyDecision {
  allowed: boolean;
  decision: 'ALLOW' | 'DENY' | 'REQUIRES_REVIEW' | 'TENANT_MISMATCH' | 'MEMORY_TYPE_PROHIBITED' | 'BRAIN_BLOCKED';
  reasons: string[];
  retentionDays?: number;
  mayInfluenceRetrieval: boolean;
  mayPromoteToKnowledge: boolean;
}
