import { getBrainProfile } from '../brains/brainRegistry';
import { canDataClassUseCapability } from '../capabilities/capabilityPolicy';
import { getIntelligenceRecords } from './intelligenceRegistry';
import type { BrainContextDenialReason, BrainContextRequest, NexusIntelligenceRecord } from './intelligenceTypes';

export interface RetrievalDecision {
  allowed: boolean;
  recordId: string;
  reasons: BrainContextDenialReason[];
}

function actorAllowed(request: BrainContextRequest): boolean {
  if (request.brainId === 'nexus_hermes') return ['ray', 'admin', 'operator', 'agent', 'unknown'].includes(request.actorRole);
  if (request.brainId === 'alpha_research') return ['ray', 'admin', 'operator', 'alpha', 'unknown'].includes(request.actorRole);
  if (request.brainId === 'client_ai') return ['client', 'client_ai', 'admin'].includes(request.actorRole);
  return ['ray', 'admin', 'operator'].includes(request.actorRole);
}

function provenancePresent(record: NexusIntelligenceRecord): boolean {
  return Boolean(record.sourceType && (record.sourceId || record.sourceUri || record.sourceTitle));
}

export function evaluateRetrieval(record: NexusIntelligenceRecord, request: BrainContextRequest): RetrievalDecision {
  const brain = getBrainProfile(request.brainId);
  const reasons: BrainContextDenialReason[] = [];
  if (!brain) return { allowed: false, recordId: record.recordId, reasons: ['BRAIN_NOT_FOUND'] };
  if (brain.status === 'BLOCKED' || brain.status === 'PROHIBITED') reasons.push('BRAIN_BLOCKED');
  if (!actorAllowed(request)) reasons.push('ACTOR_UNAUTHORIZED');
  if (brain.tenantIsolationRequired && record.tenantId && request.tenantId && record.tenantId !== request.tenantId) reasons.push('TENANT_MISMATCH');
  if (brain.tenantIsolationRequired && request.brainId === 'client_ai' && record.clientId && request.clientId && record.clientId !== request.clientId) reasons.push('TENANT_MISMATCH');
  if (!brain.allowedRecordTypes.includes(record.recordType) || brain.prohibitedRecordTypes.includes(record.recordType)) reasons.push('RECORD_TYPE_PROHIBITED');
  if (!brain.allowedKnowledgeDomains.includes(record.domain) || brain.prohibitedKnowledgeDomains.includes(record.domain)) reasons.push('DOMAIN_PROHIBITED');
  if (!brain.allowedDataClasses.includes(record.dataClass) || brain.prohibitedDataClasses.includes(record.dataClass)) reasons.push('DATA_CLASS_PROHIBITED');
  if (record.prohibitedBrainIds.includes(request.brainId) || (record.allowedBrainIds.length && !record.allowedBrainIds.includes(request.brainId))) reasons.push('POLICY_BLOCKED');
  if (request.brainId !== 'alpha_research' && ['CLAIM', 'MODEL_OUTPUT'].includes(record.recordType) && record.approvalState !== 'APPROVED') reasons.push('KNOWLEDGE_NOT_APPROVED');
  if (request.brainId === 'client_ai' && record.approvalState !== 'APPROVED') reasons.push('KNOWLEDGE_NOT_APPROVED');
  if (['EXPIRED', 'STALE'].includes(record.freshness) && record.approvalState !== 'APPROVED') reasons.push('KNOWLEDGE_STALE');
  if (record.approvalState === 'SUPERSEDED' || record.supersededBy) reasons.push('RECORD_SUPERSEDED');
  if (brain.evidenceRequired && !provenancePresent(record)) reasons.push('MISSING_PROVENANCE');
  const requestedCapabilities = request.requestedCapabilities ?? record.capabilityIds;
  for (const capabilityId of requestedCapabilities) {
    const capabilityAllowed = canDataClassUseCapability(
      capabilityId,
      record.dataClass === 'PUBLIC' ? 'PUBLIC_DATA' : record.dataClass === 'SOURCE_CODE' ? 'SOURCE_CODE' : record.dataClass === 'CLIENT_PII' ? 'CLIENT_PII' : record.dataClass === 'FINANCIAL' ? 'FINANCIAL_DATA' : 'INTERNAL_METADATA',
      request.brainId === 'alpha_research' ? 'alpha' : request.brainId === 'client_ai' ? 'client_ai' : 'admin',
    );
    if (!capabilityAllowed) reasons.push('CAPABILITY_NOT_ALLOWED');
  }
  return { allowed: reasons.length === 0, recordId: record.recordId, reasons: [...new Set(reasons)] };
}

export function retrieveIntelligenceRecords(request: BrainContextRequest): {
  allowed: NexusIntelligenceRecord[];
  denied: Array<{ record: NexusIntelligenceRecord; decision: RetrievalDecision }>;
} {
  const requestedDomains = request.requestedDomains ?? [];
  const requestedDataClasses = request.requestedDataClasses ?? [];
  const records = getIntelligenceRecords().filter((record) => {
    if (requestedDomains.length && !requestedDomains.includes(record.domain)) return false;
    if (requestedDataClasses.length && !requestedDataClasses.includes(record.dataClass)) return false;
    return true;
  });
  const allowed: NexusIntelligenceRecord[] = [];
  const denied: Array<{ record: NexusIntelligenceRecord; decision: RetrievalDecision }> = [];
  records.forEach((record) => {
    const decision = evaluateRetrieval(record, request);
    if (decision.allowed) allowed.push(record);
    else denied.push({ record, decision });
  });
  return { allowed, denied };
}
