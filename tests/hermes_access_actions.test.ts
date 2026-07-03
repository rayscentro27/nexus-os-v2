import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { clearHermesDecisionState } from '../src/lib/hermesDecisionState';
import { clearSession } from '../src/lib/hermesAdvisorSession';
import { hermesCapabilityRegistry } from '../src/lib/hermesCapabilityRegistry';
import { isSafeHermesUiAction } from '../src/lib/hermesUiActions';

const scope = { tenantId: 'access-actions-test', sessionId: 'default' };
const scopeKey = `${scope.tenantId}:${scope.sessionId}`;

describe('Hermes CEO default, access registry, and safe actions', () => {
  beforeEach(() => { clearHermesDecisionState(scopeKey); clearSession(scopeKey); });

  it('uses CEO system-health output by default and audit only on request', async () => {
    const health = await handleHermesMessage({ message: 'what is the system health', ...scope });
    expect(health.text).toMatch(/system is mostly healthy/i);
    expect(health.text).toMatch(/local reports.*not a fresh production check/i);
    expect(health.text).toMatch(/next move/i);
    expect(health.text).not.toMatch(/Audit details|Route:|reports\//i);

    const audit = await handleHermesMessage({ message: 'give me the audit version', ...scope });
    expect(audit.text).toMatch(/Audit details|Sources:|Freshness:|Timestamp:/i);
    expect(audit.text).toMatch(/system_health_registry|local_reports/i);
  });

  it('returns voice-safe reports with open_report metadata', async () => {
    const response = await handleHermesMessage({ message: 'what reports are available', ...scope });
    expect(response.text).toMatch(/I found \d+ reports/i);
    expect(response.text).not.toMatch(/reports\/[\w./-]+/i);
    expect(response.uiActions).toHaveLength(10);
    for (const action of response.uiActions || []) {
      expect(action).toMatchObject({ actionLabel: 'Open report', actionType: 'open_report', source: 'local_report_registry' });
      expect(action.reportPath || action.href).toBeTruthy();
      expect(isSafeHermesUiAction(action)).toBe(true);
    }
  });

  it('returns approval actions without exposing IDs in spoken output', async () => {
    const response = await handleHermesMessage({ message: 'do I have approvals pending', ...scope });
    expect(response.text).not.toMatch(/[0-9a-f]{8}-[0-9a-f-]{27,}/i);
    expect(response.uiActions?.length).toBeGreaterThan(0);
    for (const action of response.uiActions || []) {
      expect(action).toMatchObject({ actionLabel: 'Open approval', actionType: 'open_approval', approvalRequired: true });
      expect(action.approvalId).toBeTruthy();
      expect(isSafeHermesUiAction(action)).toBe(true);
    }
  });

  it('returns the full read-only Hermes access matrix', async () => {
    const response = await handleHermesMessage({ message: 'what can Hermes access', ...scope });
    expect(response.route).toBe('access_map');
    expect(response.text).toMatch(/connected to reports.*approvals/i);
    expect(response.accessMatrix).toEqual(hermesCapabilityRegistry);
    expect(response.accessMatrix?.length).toBeGreaterThanOrEqual(20);
    const statuses = new Set(response.accessMatrix?.map((area) => area.status));
    expect(statuses.has('connected')).toBe(true);
    expect(statuses.has('blocked')).toBe(true);
    expect(statuses.has('not_configured')).toBe(true);
    expect(statuses.has('approval_gated')).toBe(true);
    expect(response.accessMatrix?.every((area) => area.nextSafeAction && typeof area.canRead === 'boolean')).toBe(true);
    expect(response.uiActions?.[0]).toMatchObject({ actionType: 'open_access_map' });
  });

  it('keeps all emitted UI actions inside the non-mutating allowlist', async () => {
    const prompts = ['what reports are available', 'do I have approvals pending', 'what can Hermes access'];
    for (const message of prompts) {
      const response = await handleHermesMessage({ message, ...scope });
      for (const action of response.uiActions || []) {
        expect(isSafeHermesUiAction(action)).toBe(true);
        expect(action.actionType).not.toMatch(/send|publish|charge|schedule|trade|deploy|delete|approve|reject/i);
      }
    }
  });

  it('keeps report review voice-safe after opening the session', async () => {
    const list = await handleHermesMessage({ message: 'what reports are available', ...scope });
    expect(list.uiActions?.length).toBeGreaterThan(0);
    const review = await handleHermesMessage({ message: 'can we review them', ...scope });
    expect(review.text).not.toMatch(/reports\/[\w./-]+/i);
  });
});
