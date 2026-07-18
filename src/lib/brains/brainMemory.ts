import { getBrainProfile } from './brainRegistry';
import type { BrainMemoryPolicyDecision, BrainMemoryType } from './brainTypes';

export function evaluateMemoryPolicy(
  brainId: string,
  memoryType: BrainMemoryType,
  action: 'read' | 'write',
  options: { tenantId?: string; recordTenantId?: string; sensitive?: boolean } = {},
): BrainMemoryPolicyDecision {
  const brain = getBrainProfile(brainId);
  if (!brain || brain.status === 'BLOCKED' || brain.status === 'PROHIBITED') {
    return { allowed: false, decision: 'BRAIN_BLOCKED', reasons: ['Brain is missing, blocked, or prohibited.'], mayInfluenceRetrieval: false, mayPromoteToKnowledge: false };
  }
  if (!brain.allowedMemoryTypes.includes(memoryType)) {
    return { allowed: false, decision: 'MEMORY_TYPE_PROHIBITED', reasons: [`${brain.name} cannot ${action} ${memoryType}.`], mayInfluenceRetrieval: false, mayPromoteToKnowledge: false };
  }
  if (brain.tenantIsolationRequired && options.tenantId && options.recordTenantId && options.tenantId !== options.recordTenantId) {
    return { allowed: false, decision: 'TENANT_MISMATCH', reasons: ['Memory tenant scope does not match actor tenant.'], mayInfluenceRetrieval: false, mayPromoteToKnowledge: false };
  }
  if (options.sensitive && brainId === 'alpha_research') {
    return { allowed: false, decision: 'DENY', reasons: ['Alpha memory cannot store sensitive Nexus or client data.'], mayInfluenceRetrieval: false, mayPromoteToKnowledge: false };
  }
  return {
    allowed: true,
    decision: 'ALLOW',
    reasons: [`${brain.name} may ${action} ${memoryType} within policy scope.`],
    retentionDays: memoryType === 'SELECTION_MEMORY' ? 7 : memoryType === 'CLIENT_JOURNEY_MEMORY' ? 365 : 90,
    mayInfluenceRetrieval: true,
    mayPromoteToKnowledge: false,
  };
}

export function memoryRequiresKnowledgeReview(memoryType: BrainMemoryType): boolean {
  return ['EXECUTIVE_DECISION_MEMORY', 'RESEARCH_MEMORY', 'DEPARTMENT_WORK_MEMORY'].includes(memoryType);
}
