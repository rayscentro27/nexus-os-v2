import { describe, expect, it } from 'vitest';
import { getBrainProfile, getBrainProfiles } from '../src/lib/brains/brainRegistry';

describe('AI Brain Profile Registry', () => {
  it('contains required active brain profiles and planned department templates', () => {
    const profiles = getBrainProfiles();
    const ids = profiles.map((profile) => profile.brainId);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toContain('nexus_hermes');
    expect(ids).toContain('alpha_research');
    expect(ids).toContain('client_ai');
    expect(profiles.filter((profile) => profile.role === 'DEPARTMENT_AI').length).toBeGreaterThanOrEqual(8);
    expect(profiles.filter((profile) => profile.role === 'DEPARTMENT_AI').every((profile) => profile.status !== 'ACTIVE')).toBe(true);
  });

  it('preserves Hermes, Alpha, and Client AI authority boundaries', () => {
    const hermes = getBrainProfile('nexus_hermes')!;
    const alpha = getBrainProfile('alpha_research')!;
    const client = getBrainProfile('client_ai')!;
    expect(hermes.mayApproveKnowledge).toBe(false);
    expect(hermes.mayExecuteWork).toBe(false);
    expect(alpha.mayUseSupabase).toBe(false);
    expect(alpha.mayAccessClientPii).toBe(false);
    expect(alpha.prohibitedDataClasses).toContain('CLIENT_PII');
    expect(client.tenantIsolationRequired).toBe(true);
    expect(client.prohibitedDataClasses).toContain('EXECUTIVE');
    expect(client.prohibitedKnowledgeDomains).toContain('alpha_raw_research');
  });
});
