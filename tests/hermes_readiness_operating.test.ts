import { describe, it, expect } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';

describe('Nexus Readiness Operating Commands', () => {
  it('is credit repair ready — CEO answer with readiness status', async () => {
    const response = await handleHermesMessage({ message: 'is credit repair ready?' });
    expect(response.route).toBe('readiness_operating_status');
    expect(response.text).toMatch(/credit repair/i);
    expect(response.text).toMatch(/partial|blocked|not ready|missing/i);
    expect(response.text).not.toMatch(/error|exception|undefined|NaN/i);
  });

  it('is business funding ready — CEO answer with readiness status', async () => {
    const response = await handleHermesMessage({ message: 'is business funding ready?' });
    expect(response.route).toBe('readiness_operating_status');
    expect(response.text).toMatch(/business funding/i);
    expect(response.text).toMatch(/partial|blocked|not ready|missing/i);
    expect(response.text).not.toMatch(/error|exception|undefined|NaN/i);
  });

  it('can we sell the $97 readiness review — clear answer with manual-first recommendation', async () => {
    const response = await handleHermesMessage({ message: 'can we sell the $97 readiness review now?' });
    expect(response.route).toBe('readiness_operating_status');
    expect(response.text).toMatch(/partial|manual|yes.*but|not yet/i);
    expect(response.text).toMatch(/manual|conversation|by hand/i);
  });

  it('what parts are manual — lists manual steps', async () => {
    const response = await handleHermesMessage({ message: 'what parts are manual?' });
    expect(response.route).toBe('readiness_operating_status');
    expect(response.text).toMatch(/manual/i);
    expect(response.text).toMatch(/credit|funding|business/i);
  });

  it('prepare specialist handoff for business funding — draft-only, no execution', async () => {
    const response = await handleHermesMessage({ message: 'prepare specialist handoff for business funding' });
    expect(response.text).toMatch(/specialist|handoff|draft/i);
    expect(response.text).toMatch(/not created|not saved|not assigned|not sent|conversation-only/i);
  });

  it('give me the audit version — shows paths and technical details', async () => {
    const response = await handleHermesMessage({ message: 'give me the audit version' });
    expect(response.text).toMatch(/source|file|path|src\/|config\/|report/i);
  });
});
