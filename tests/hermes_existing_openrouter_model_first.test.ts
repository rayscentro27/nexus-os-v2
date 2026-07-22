import { beforeEach, describe, expect, it, vi } from 'vitest';
import { hermesChat } from '../src/lib/hermesProviders';
import { runHermesModelFirstConversation } from '../src/lib/hermesModelFirst/hermesModelFirstController';

vi.mock('../src/lib/hermesProviders', () => ({
  hermesChat: vi.fn(),
}));

const mockedHermesChat = vi.mocked(hermesChat);

describe('Hermes existing OpenRouter model-first controller', () => {
  beforeEach(() => {
    vi.unstubAllEnvs();
    mockedHermesChat.mockReset();
  });

  it('sends ordinary language to the existing hermes-chat model gateway in Ray-only pilot mode', async () => {
    vi.stubEnv('VITE_HERMES_MODEL_FIRST_MODE', 'RAY_ONLY_PILOT');
    mockedHermesChat.mockResolvedValue({
      configured: true,
      text: 'A velocipede is an early human-powered wheeled vehicle, often a predecessor to the bicycle.',
      metadata: {
        provider: 'openrouter',
        model: 'openai/gpt-4o-mini',
        estimatedInputTokens: 24,
        estimatedOutputTokens: 22,
      },
    });

    const result = await runHermesModelFirstConversation({
      message: 'What is a velocipede?',
      actorRole: 'admin',
      sessionId: 'hermes-session-test-123',
      recentHistory: [{ role: 'user', content: 'good morning' }],
    });

    expect(result.usedModelFirst).toBe(true);
    expect(mockedHermesChat).toHaveBeenCalledTimes(1);
    expect(mockedHermesChat.mock.calls[0][0]).toBe('What is a velocipede?');
    expect(mockedHermesChat.mock.calls[0][1]).toBe('model_first_conversation');
    expect(mockedHermesChat.mock.calls[0][2]).toMatchObject({ conversationId: 'hermes-session-test-123' });
    expect(result.response?.responseStrategy).toBe('APPROVED_MODEL_DIRECT');
    expect(result.response?.contextUsed).toContain('provider:openrouter');
    expect(result.response?.contextUsed).toContain('model:openai/gpt-4o-mini');
  });

  it('does not invoke the model-first path when the feature flag is off', async () => {
    vi.stubEnv('VITE_HERMES_MODEL_FIRST_MODE', 'OFF');
    const result = await runHermesModelFirstConversation({
      message: 'What is a hovercraft?',
      actorRole: 'admin',
    });

    expect(result.usedModelFirst).toBe(false);
    expect(mockedHermesChat).not.toHaveBeenCalled();
  });

  it('returns truthful degraded state instead of a legacy generic fallback when the provider is unavailable', async () => {
    vi.stubEnv('VITE_HERMES_MODEL_FIRST_MODE', 'RAY_ONLY_PILOT');
    mockedHermesChat.mockResolvedValue({ configured: false, text: '', metadata: { provider: 'openrouter', model: 'none' } });

    const result = await runHermesModelFirstConversation({
      message: 'What is a hydrofoil?',
      actorRole: 'admin',
    });

    expect(result.usedModelFirst).toBe(true);
    expect(result.response?.mode).toBe('MODEL_FIRST_DEGRADED');
    expect(result.response?.text).toMatch(/conversational model is temporarily unavailable/i);
    expect(result.response?.text).not.toMatch(/authorized Nexus context/i);
  });
});
