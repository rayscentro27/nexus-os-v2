import { describe, expect, it } from 'vitest';
import { getHermesModelFirstRuntimeStatus } from '../src/lib/hermesModelFirst/hermesModelFirstConfig';

describe('Hermes model-first runtime configuration', () => {
  it('blocks activation when OpenRouter and Letta runtime are absent', () => {
    const status = getHermesModelFirstRuntimeStatus({});
    expect(status.modelFirstMode).toBe('OFF');
    expect(status.openRouter.state).toBe('MISSING_KEY');
    expect(status.letta.state).toBe('MISSING_MODE');
    expect(status.blockers).toEqual(['BLOCKED_PENDING_OPENROUTER_KEY', 'BLOCKED_PENDING_LETTA_RUNTIME']);
    expect(status.activationBlocked).toBe(true);
  });

  it('recognizes hosted Letta runtime requirements without exposing the key', () => {
    const status = getHermesModelFirstRuntimeStatus({
      OPENROUTER_API_KEY: 'present',
      HERMES_MODEL_FIRST_MODE: 'RAY_ONLY_PILOT',
      LETTA_RUNTIME_MODE: 'HOSTED',
      LETTA_API_KEY: 'present',
      LETTA_HERMES_AGENT_ID: 'agent-123',
      HERMES_OPENROUTER_MODEL: 'openai/gpt-5.6-luna',
    });
    expect(status.modelFirstMode).toBe('RAY_ONLY_PILOT');
    expect(status.openRouter.apiKeyPresent).toBe(true);
    expect(status.letta.apiKeyPresent).toBe(true);
    expect(status.letta.hermesAgentIdPresent).toBe(true);
    expect(status.letta.state).toBe('READY');
    expect(status.blockers).toEqual([]);
  });

  it('keeps Ray-only pilot cost defaults bounded', () => {
    const status = getHermesModelFirstRuntimeStatus({});
    expect(status.openRouter.maxOutputTokens).toBe(600);
    expect(status.openRouter.dailyLimitUsd).toBe(0.5);
    expect(status.openRouter.monthlyLimitUsd).toBe(10);
  });
});
