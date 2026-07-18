import { assembleBrainContext } from './contextAssembler';
import type { BrainContextRequest } from './intelligenceTypes';

export interface RetrievalEvaluationResult {
  fixtureId: string;
  passed: boolean;
  summary: string;
}

export function runRetrievalEvaluationFixtures(): RetrievalEvaluationResult[] {
  const fixtures: Array<{ fixtureId: string; request: BrainContextRequest; expectExcluded?: string; expectIncluded?: string }> = [
    { fixtureId: 'approved_hermes_policy', request: { brainId: 'nexus_hermes', actorRole: 'admin', query: 'authority policy', requestedDomains: ['executive'] }, expectIncluded: 'policy_authority_model' },
    { fixtureId: 'alpha_raw_not_hermes_fact', request: { brainId: 'nexus_hermes', actorRole: 'admin', query: 'alpha claim', requestedDomains: ['public_research'] }, expectExcluded: 'claim_alpha_raw_market_pattern' },
    { fixtureId: 'client_blocks_executive', request: { brainId: 'client_ai', actorRole: 'client', tenantId: 'synthetic', clientId: 'persona_a', query: 'executive', requestedDomains: ['executive'] }, expectExcluded: 'policy_authority_model' },
    { fixtureId: 'missing_provenance_flag', request: { brainId: 'nexus_hermes', actorRole: 'admin', query: 'missing provenance', requestedDomains: ['knowledge'] }, expectExcluded: 'evidence_missing_provenance_fixture' },
  ];
  return fixtures.map((fixture) => {
    const pkg = assembleBrainContext(fixture.request);
    const included = [...pkg.approvedKnowledge, ...pkg.evidence, ...pkg.observations].some((record) => record.recordId === fixture.expectIncluded);
    const excluded = pkg.excluded.some((item) => item.recordId === fixture.expectExcluded);
    const passed = fixture.expectIncluded ? included : excluded;
    return {
      fixtureId: fixture.fixtureId,
      passed,
      summary: passed ? 'Retrieval policy behaved as expected.' : 'Retrieval policy did not match expected inclusion/exclusion.',
    };
  });
}
