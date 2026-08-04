import { describe, expect, it } from 'vitest';
import { answerOperationalQuestion, getBundledOperationalSnapshot, HERMES_OPERATIONAL_INTELLIGENCE_VERSION } from '../src/lib/nexusOperationalTruth';

describe('Hermes operational truth upgrade', () => {
  it('answers process questions from operational snapshots with provenance', () => {
    const answer = answerOperationalQuestion('What processes are currently running on Nexus?');
    expect(answer.handled).toBe(true);
    expect(answer.text).toMatch(/Source:/);
    expect(answer.text).toMatch(/Last updated:/);
    expect(answer.text).toMatch(/Record count:/);
    expect(answer.text).toMatch(/Unavailable sources:/);
    expect(answer.text).not.toMatch(/typically|in a system like/i);
  });

  it('does not claim production has no failures from a bundled snapshot alone', () => {
    const answer = answerOperationalQuestion('Which processes failed?');
    expect(answer.handled).toBe(true);
    expect(answer.text).toMatch(/bundled snapshot|not proof|stale/i);
  });

  it('keeps versions and registry freshness explicit', () => {
    const answer = answerOperationalQuestion('What version of Hermes is running? Is Supabase connected?');
    const snapshot = getBundledOperationalSnapshot();
    expect(HERMES_OPERATIONAL_INTELLIGENCE_VERSION).toMatch(/Hermes Operational Intelligence/);
    expect(['CURRENT', 'STALE', 'UNKNOWN']).toContain(snapshot.freshness);
    expect(answer.text).toMatch(/require live probes/i);
  });
});
