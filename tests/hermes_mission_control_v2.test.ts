import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { hermesMissionControlData, normalizeMissionControlWorkerStatus } from '../src/data/hermesMissionControlData';

describe('Hermes Mission Control V2', () => {
  it('uses the proven Phase 9 opportunity and report-backed metrics', () => {
    expect(hermesMissionControlData.opportunity.id).toBe('unclecode_crawl4ai');
    expect(hermesMissionControlData.opportunity.status).toBe('PILOT_PROPOSED');
    expect(hermesMissionControlData.activeOpportunityCount).toBe(1);
    expect(hermesMissionControlData.research.evidence_count).toBe(1);
    expect(hermesMissionControlData.research.duplicates_removed).toBe(4);
    expect(hermesMissionControlData.creative.selected_territory).toBe('Scout Brief');
    expect(hermesMissionControlData.buildSpec.status).toBe('PASS');
  });

  it('exposes worker truth without attempting provider configuration', () => {
    expect(hermesMissionControlData.workers.map((worker) => worker.id)).toEqual([
      'opencode', 'codex', 'mimo', 'local_python', 'openhands',
    ]);
    expect(hermesMissionControlData.workers.find((worker) => worker.id === 'codex')?.status).toBe('AVAILABLE');
    expect(hermesMissionControlData.workers.find((worker) => worker.id === 'local_python')?.status).toBe('AVAILABLE');
    expect(hermesMissionControlData.workers.find((worker) => worker.id === 'openhands')?.status).toBe('NOT_INSTALLED');
  });

  it('preserves every supported worker classification for the status surface', () => {
    expect([
      'AVAILABLE', 'INSTALLED_UNPROVEN', 'AUTH_BLOCKED', 'RATE_LIMITED', 'NOT_INSTALLED', 'UNAVAILABLE',
    ].map(normalizeMissionControlWorkerStatus)).toEqual([
      'AVAILABLE', 'INSTALLED_UNPROVEN', 'AUTH_BLOCKED', 'RATE_LIMITED', 'NOT_INSTALLED', 'UNAVAILABLE',
    ]);
    expect(normalizeMissionControlWorkerStatus('invented_status')).toBe('UNKNOWN');
  });

  it('keeps Mission Control read-only and client boundaries intact', () => {
    const ui = readFileSync('src/components/command-center/HermesMissionControlV2.tsx', 'utf8');
    const app = readFileSync('src/app/App.tsx', 'utf8');
    expect(ui).toContain('data-testid="hermes-mission-control-v2"');
    expect(ui).toContain('No provider actions are available here.');
    expect(app).toContain("'/admin/command-center-v2'");
    expect(ui).not.toMatch(/supabase|client_profiles|insert\(|update\(|delete\(/i);
  });
});
