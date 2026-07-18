import { evaluateMemoryPolicy } from '../brains/brainMemory';
import { retrieveIntelligenceRecords } from './knowledgeRetrieval';
import type { BrainContextPackage, BrainContextRequest, IntelligenceEvidenceState, NexusIntelligenceRecord } from './intelligenceTypes';

function recordLabel(record: NexusIntelligenceRecord): string {
  return `${record.recordType}: ${record.title} (${record.evidenceState}, ${record.freshness})`;
}

function evidenceState(records: NexusIntelligenceRecord[]): IntelligenceEvidenceState {
  if (!records.length) return 'UNKNOWN';
  if (records.some((record) => record.evidenceState === 'LIVE')) return 'LIVE';
  if (records.every((record) => record.evidenceState === 'REPORT_BACKED')) return 'REPORT_BACKED';
  if (records.some((record) => record.evidenceState === 'BLOCKED')) return 'BLOCKED';
  return records[0].evidenceState;
}

export function assembleBrainContext(request: BrainContextRequest): BrainContextPackage {
  const result = retrieveIntelligenceRecords(request);
  const approvedKnowledge = result.allowed.filter((record) => record.recordType === 'APPROVED_KNOWLEDGE' || record.recordType === 'POLICY');
  const evidence = result.allowed.filter((record) => record.recordType === 'EVIDENCE' || record.recordType === 'SOURCE');
  const observations = result.allowed.filter((record) => record.recordType === 'OBSERVATION');
  const memories = result.allowed
    .filter((record) => record.recordType === 'MEMORY')
    .filter((record) => evaluateMemoryPolicy(request.brainId, 'SELECTION_MEMORY', 'read', { tenantId: request.tenantId, recordTenantId: record.tenantId ?? undefined }).allowed)
    .map((record) => ({ memoryType: 'SELECTION_MEMORY', summary: record.summary, sourceId: record.recordId }));
  const recommendations = result.allowed.filter((record) => record.recordType === 'RECOMMENDATION').map(recordLabel);
  return {
    brainId: request.brainId,
    query: request.query,
    approvedKnowledge,
    evidence,
    observations,
    memories,
    excluded: result.denied.map(({ record, decision }) => ({
      recordId: record.recordId,
      reason: decision.reasons.join(', '),
    })),
    facts: [...approvedKnowledge, ...evidence, ...observations].map(recordLabel),
    policies: approvedKnowledge.filter((record) => record.recordType === 'POLICY').map(recordLabel),
    recommendations,
    unknowns: result.denied.filter(({ decision }) => decision.reasons.includes('MISSING_PROVENANCE')).map(({ record }) => `${record.title}: missing provenance`),
    conflicts: result.allowed.filter((record) => record.conflictingRecordIds.length).map((record) => `${record.title} conflicts with ${record.conflictingRecordIds.join(', ')}`),
    freshnessSummary: result.allowed.length ? `${result.allowed.filter((record) => record.freshness === 'CURRENT').length} current, ${result.allowed.filter((record) => record.freshness !== 'CURRENT').length} aging/stale/unknown` : 'No retrievable records',
    evidenceState: evidenceState(result.allowed),
    generatedAt: new Date().toISOString(),
  };
}
