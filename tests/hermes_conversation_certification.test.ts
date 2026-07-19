import { describe, expect, it } from 'vitest';
import { getHermesCertificationCorpus } from '../src/lib/hermes/hermesResponseQuality';
import { buildHermesConversationHealthSummary, runHermesConversationCertification } from '../src/lib/hermes/hermesConversationEngine';
import { getCapability } from '../src/lib/capabilities/capabilityRegistry';

describe('Hermes Wave 4A conversation certification', () => {
  it('passes the durable certification thresholds', () => {
    const summary = runHermesConversationCertification();
    expect(summary.fixtureCount).toBeGreaterThanOrEqual(10);
    expect(summary.overallScore).toBeGreaterThanOrEqual(95);
    expect(summary.historicalRegressionScore).toBe(100);
    expect(summary.actionSeparationScore).toBe(100);
    expect(summary.statusHonestyScore).toBe(100);
    expect(summary.repetitionScore).toBe(100);
    expect(summary.failures).toEqual([]);
  });

  it('covers the required conversation groups', () => {
    const groups = new Set(getHermesCertificationCorpus().map((item) => item.group));
    for (const group of ['greetings', 'historical', 'executive_advice', 'selection', 'action_separation', 'status_honesty', 'page_context']) {
      expect(groups.has(group)).toBe(true);
    }
  });

  it('surfaces conversation health for Founder Mode without client controls', () => {
    const health = buildHermesConversationHealthSummary();
    expect(health.canonicalPipeline).toMatch(/hermesConversationEngine/);
    expect(health.providerAvailability).toMatch(/external model providers not activated/i);
    expect(health.knownRisks.join(' ')).not.toMatch(/install|credential value/i);
  });

  it('registers Wave 4A capabilities without external activation', () => {
    expect(getCapability('hermes_conversation_engine')).toMatchObject({ activationMode: 'ACTIVE', hermesMayExecute: false });
    expect(getCapability('hermes_conversation_certification')).toMatchObject({ activationMode: 'TEST_ONLY', healthStatus: 'HEALTHY' });
    expect(getCapability('github_mcp_reader')).toMatchObject({ activationMode: 'NOT_CONFIGURED' });
    expect(getCapability('github_mcp_writer')).toMatchObject({ activationMode: 'APPROVAL_GATED', hermesMayExecute: false });
  });
});
