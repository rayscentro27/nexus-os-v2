import { describe, expect, it } from 'vitest';
import { getBrainProfile } from '../src/lib/brains/brainRegistry';
import { evaluateBrainHandoff } from '../src/lib/brains/brainHandoffs';
import { evaluateMemoryPolicy, memoryRequiresKnowledgeReview } from '../src/lib/brains/brainMemory';
import { assembleBrainContext } from '../src/lib/intelligence/contextAssembler';
import { getIntelligenceRecords } from '../src/lib/intelligence/intelligenceRegistry';
import { evaluateRetrieval } from '../src/lib/intelligence/knowledgeRetrieval';
import { buildKnowledgeHealthSummary } from '../src/lib/intelligence/knowledgeHealth';
import { runRetrievalEvaluationFixtures } from '../src/lib/intelligence/retrievalEvaluation';
import { validateStructuredIntelligenceResult } from '../src/lib/intelligence/structuredOutput';

describe('Wave 3 intelligence registry', () => {
  it('keeps intelligence record IDs unique and separates core record types', () => {
    const records = getIntelligenceRecords();
    const ids = records.map((record) => record.recordId);
    expect(new Set(ids).size).toBe(ids.length);
    ['SOURCE', 'EVIDENCE', 'CLAIM', 'OBSERVATION', 'APPROVED_KNOWLEDGE', 'POLICY', 'RECOMMENDATION', 'MEMORY'].forEach((type) => {
      expect(records.some((record) => record.recordType === type)).toBe(true);
    });
  });

  it('requires provenance and marks superseded/stale knowledge distinctly', () => {
    const records = getIntelligenceRecords();
    expect(records.some((record) => record.approvalState === 'SUPERSEDED' && record.supersededBy)).toBe(true);
    expect(records.some((record) => record.recordId === 'evidence_missing_provenance_fixture' && !record.sourceId && !record.sourceUri)).toBe(true);
    expect(buildKnowledgeHealthSummary().missingProvenance).toBeGreaterThan(0);
  });
});

describe('Wave 3 retrieval policy', () => {
  it('retrieves approved Hermes policy and excludes unapproved Alpha claims from Hermes facts', () => {
    const context = assembleBrainContext({ brainId: 'nexus_hermes', actorRole: 'admin', query: 'policy', requestedDomains: ['executive', 'public_research'] });
    expect(context.approvedKnowledge.some((record) => record.recordId === 'policy_authority_model')).toBe(true);
    expect(context.excluded.some((item) => item.recordId === 'claim_alpha_raw_market_pattern' && item.reason.includes('KNOWLEDGE_NOT_APPROVED'))).toBe(true);
  });

  it('blocks client AI from Executive records and wrong tenant records', () => {
    const context = assembleBrainContext({ brainId: 'client_ai', actorRole: 'client', tenantId: 'other', clientId: 'other', query: 'client evidence' });
    expect(context.excluded.some((item) => item.recordId === 'policy_authority_model')).toBe(true);
    expect(context.excluded.some((item) => item.recordId === 'observation_document_processing_recheck' && item.reason.includes('TENANT_MISMATCH'))).toBe(true);
  });

  it('flags superseded, stale, prohibited, and missing-provenance records', () => {
    const records = getIntelligenceRecords();
    const superseded = records.find((record) => record.recordId === 'knowledge_superseded_old_credit_wrapper')!;
    const missing = records.find((record) => record.recordId === 'evidence_missing_provenance_fixture')!;
    expect(evaluateRetrieval(superseded, { brainId: 'nexus_hermes', actorRole: 'admin', query: 'superseded' }).reasons).toContain('RECORD_SUPERSEDED');
    expect(evaluateRetrieval(missing, { brainId: 'nexus_hermes', actorRole: 'admin', query: 'missing' }).reasons).toContain('MISSING_PROVENANCE');
  });

  it('runs native retrieval evaluation fixtures', () => {
    const results = runRetrievalEvaluationFixtures();
    expect(results.every((result) => result.passed)).toBe(true);
  });
});

describe('Wave 3 memory and handoff boundaries', () => {
  it('separates Hermes, Alpha, and Client AI memory', () => {
    expect(evaluateMemoryPolicy('nexus_hermes', 'RESEARCH_MEMORY', 'read').allowed).toBe(false);
    expect(evaluateMemoryPolicy('alpha_research', 'EXECUTIVE_DECISION_MEMORY', 'read').allowed).toBe(false);
    expect(evaluateMemoryPolicy('client_ai', 'CLIENT_JOURNEY_MEMORY', 'read', { tenantId: 'a', recordTenantId: 'b' }).decision).toBe('TENANT_MISMATCH');
    expect(memoryRequiresKnowledgeReview('RESEARCH_MEMORY')).toBe(true);
  });

  it('prevents Alpha findings from becoming Hermes facts automatically', () => {
    const decision = evaluateBrainHandoff('alpha_research', 'nexus_hermes', ['claim_alpha_raw_market_pattern']);
    expect(decision.allowed).toBe(false);
    expect(decision.event.action).toBe('BRAIN_HANDOFF_DENIED');
    expect(decision.reasons.join(' ')).toMatch(/require review/i);
  });
});

describe('Structured output foundation', () => {
  it('accepts valid structured output and rejects malformed output with sanitized errors', () => {
    const ok = validateStructuredIntelligenceResult({ title: 'Finding', confidence: 'HIGH' }, (candidate) => {
      if (typeof candidate === 'object' && candidate && 'title' in candidate) return { success: true, data: candidate as { title: string; confidence: string } };
      return { success: false, errors: [{ code: 'MISSING_TITLE', message: 'title is required' }] };
    }, { evidenceIds: ['evidence_repo_intelligence_registry'] });
    expect(ok.success).toBe(true);
    expect(ok.evidenceIds).toContain('evidence_repo_intelligence_registry');

    const bad = validateStructuredIntelligenceResult({}, () => ({ success: false, errors: [{ path: 'title', code: 'MISSING_TITLE', message: 'title is required' }] }), { attempts: 10 });
    expect(bad.success).toBe(false);
    expect(bad.attempts).toBe(3);
    expect(JSON.stringify(bad)).not.toMatch(/password|token|sk_live_/i);
  });
});

describe('Document evidence processing certification record', () => {
  it('does not leave document processing in needs-recheck status', () => {
    const health = buildKnowledgeHealthSummary();
    expect(health.documentEvidenceStatus).toBe('CERTIFIED_AND_UNCHANGED');
  });
});
