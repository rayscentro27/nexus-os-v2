import { describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';

describe('GoClear manual-first activation', () => {
  it('reports launch readiness as manual-ready, not automated, with one next step', async () => {
    const response = await handleHermesMessage({ message: 'is GoClear ready to launch?' });

    expect(response.route).toBe('readiness_operating_status');
    expect(response.text).toMatch(/manual-ready/i);
    expect(response.text).toMatch(/not automated|no live/i);
    expect(response.text.match(/next step:/gi)).toHaveLength(1);
  });

  it('honestly answers whether the $97 review can be sold', async () => {
    const response = await handleHermesMessage({ message: 'can we start selling the $97 review?' });

    expect(response.text).toMatch(/manual-ready/i);
    expect(response.text).toMatch(/does not process or confirm a live payment/i);
    expect(response.text).not.toMatch(/payment (?:was|is) confirmed|email (?:was|is) sent/i);
  });

  it('reports only the safe processes that ran', async () => {
    const response = await handleHermesMessage({ message: 'what processes ran?' });

    expect(response.text).toMatch(/credit repair.*credit profile.*business profile.*funding readiness/is);
    expect(response.text).toMatch(/research-to-money|readiness score/i);
    expect(response.text).toMatch(/no external action/i);
    expect(response.uiActions?.[0]?.actionType).toBe('open_report');
  });

  it('opens client intake through safe action metadata', async () => {
    const response = await handleHermesMessage({ message: 'open the client intake' });

    expect(response.uiActions?.[0]).toMatchObject({
      actionType: 'open_intake',
      href: '#readiness-intake',
    });
    expect(response.text).toMatch(/local draft only|nothing is sent externally/i);
  });

  it('returns marketing gaps and one low-cost next action', async () => {
    const response = await handleHermesMessage({ message: 'what marketing is missing?' });

    expect(response.text).toMatch(/landing|cta/i);
    expect(response.text).toMatch(/referral.*inactive|follow-up.*not configured/is);
    expect(response.text).toMatch(/warm-lead script/i);
    expect(response.text.match(/next step:/gi)).toHaveLength(1);
  });

  it('prepares specialist handoff as draft-only without execution', async () => {
    const response = await handleHermesMessage({ message: 'prepare specialist handoff' });

    expect(response.text).toMatch(/draft-only/i);
    expect(response.text).toMatch(/ray review/i);
    expect(response.text).not.toMatch(/assigned successfully|handoff sent|executed successfully/i);
  });

  it('shows raw paths only for an explicit audit request', async () => {
    const normal = await handleHermesMessage({ message: 'is GoClear ready to launch?' });
    const audit = await handleHermesMessage({ message: 'give me the audit version' });

    expect(normal.text).not.toMatch(/(?:src|reports)\//i);
    expect(audit.text).toMatch(/reports\/goclear_activation\/goclear_credit_funding_activation_audit\.md/i);
    expect(audit.text).toMatch(/src\/lib\/hermesLocalOperatingCommands\.ts/i);
  });
});
