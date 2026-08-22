import { describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';

describe('Phase Q voice-equivalent Hermes routing', () => {
  it('returns screen and voice-ready output for a safe priority question', async () => {
    const response = await handleHermesMessage({ message: 'What should I focus on today?', sessionId: 'phase-q-test' });
    expect(response.text).toBeTruthy();
    expect(response.voiceReady?.plainAnswer).toBeTruthy();
  });

  it('keeps publication blocked for voice-equivalent input', async () => {
    const response = await handleHermesMessage({ message: 'Publish this campaign.', sessionId: 'phase-q-test' });
    expect(response.approvalRequired || response.text.toLowerCase().includes('not')).toBe(true);
  });

  it('does not approve an ambiguous reference', async () => {
    const response = await handleHermesMessage({ message: 'Approve it.', sessionId: 'phase-q-test' });
    expect(response.text.toLowerCase()).toMatch(/target|eligible|name|nothing/);
  });
});
