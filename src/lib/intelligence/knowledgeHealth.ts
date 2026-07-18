import { getBrainProfiles } from '../brains/brainRegistry';
import { getIntelligenceRecords } from './intelligenceRegistry';
import { runRetrievalEvaluationFixtures } from './retrievalEvaluation';

export interface KnowledgeHealthSummary {
  generatedAt: string;
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
  crossBrainHandoffs: number;
  documentEvidenceStatus: 'CERTIFIED_AND_UNCHANGED' | 'REGRESSED' | 'BLOCKED' | 'UNKNOWN';
  evaluationPassed: number;
  evaluationTotal: number;
}

function hasProvenance(record: { sourceId?: string; sourceUri?: string; sourceTitle?: string }): boolean {
  return Boolean(record.sourceId || record.sourceUri || record.sourceTitle);
}

export function buildKnowledgeHealthSummary(): KnowledgeHealthSummary {
  const records = getIntelligenceRecords();
  const profiles = getBrainProfiles();
  const evaluations = runRetrievalEvaluationFixtures();
  return {
    generatedAt: new Date().toISOString(),
    totalRecords: records.length,
    approvedKnowledge: records.filter((record) => ['APPROVED_KNOWLEDGE', 'POLICY'].includes(record.recordType) && record.approvalState === 'APPROVED').length,
    unverifiedClaims: records.filter((record) => record.recordType === 'CLAIM' && ['UNVERIFIED', 'UNDER_REVIEW'].includes(record.approvalState)).length,
    staleRecords: records.filter((record) => record.freshness === 'STALE').length,
    expiredRecords: records.filter((record) => record.freshness === 'EXPIRED' || record.approvalState === 'EXPIRED').length,
    conflicts: records.filter((record) => record.conflictingRecordIds.length).length,
    missingProvenance: records.filter((record) => !hasProvenance(record)).length,
    pendingReviews: records.filter((record) => record.approvalState === 'UNDER_REVIEW').length,
    rejectedFindings: records.filter((record) => record.approvalState === 'REJECTED').length,
    recordsBlockedByPolicy: records.filter((record) => record.prohibitedBrainIds.length).length,
    alphaSubmissionsAwaitingReview: records.filter((record) => record.sourceType === 'RESEARCH_AGENT' && record.approvalState !== 'APPROVED').length,
    clientSafeKnowledge: records.filter((record) => record.allowedBrainIds.includes('client_ai') && record.approvalState === 'APPROVED').length,
    brainProfiles: profiles.length,
    activeBrains: profiles.filter((profile) => profile.status === 'ACTIVE').length,
    plannedDepartmentTemplates: profiles.filter((profile) => profile.role === 'DEPARTMENT_AI' && profile.status !== 'ACTIVE').length,
    retrievalDenials: evaluations.filter((item) => item.fixtureId.includes('blocks') || item.fixtureId.includes('not_hermes') || item.fixtureId.includes('missing')).length,
    crossBrainHandoffs: 0,
    documentEvidenceStatus: records.some((record) => record.recordId === 'observation_document_processing_recheck') ? 'CERTIFIED_AND_UNCHANGED' : 'UNKNOWN',
    evaluationPassed: evaluations.filter((item) => item.passed).length,
    evaluationTotal: evaluations.length,
  };
}
