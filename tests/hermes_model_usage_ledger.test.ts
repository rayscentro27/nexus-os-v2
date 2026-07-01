/**
 * Tests for Hermes Model Usage Ledger.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  logModelAttempt,
  logModelSkipped,
  getUsageEntries,
  getTotalTokensUsed,
  getRecentUsageSummary,
  getModelActivityAnswer,
  clearUsageLog,
} from '../src/lib/hermesModelUsageLedger';

// Mock localStorage for test environment
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();
vi.stubGlobal('localStorage', localStorageMock);

describe('Usage Ledger', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it('logs model call attempts', () => {
    logModelAttempt({
      route: 'primary_model',
      modelProvider: 'openrouter',
      modelName: 'gpt-4o-mini',
      promptType: 'strategy',
      estimatedInputTokens: 500,
      estimatedOutputTokens: 200,
      contextSources: ['supabase_summary'],
      wasModelCalled: true,
      skippedReason: '',
      fallbackUsed: '',
      costEstimateAvailable: false,
      error: '',
      durationMs: 1200,
    });

    const entries = getUsageEntries();
    expect(entries.length).toBe(1);
    expect(entries[0].route).toBe('primary_model');
    expect(entries[0].wasModelCalled).toBe(true);
    expect(entries[0].modelProvider).toBe('openrouter');
  });

  it('logs skipped no_model decisions', () => {
    logModelSkipped('Casual question — local conversation brain handles this.', 'local_answer');

    const entries = getUsageEntries();
    expect(entries.length).toBe(1);
    expect(entries[0].wasModelCalled).toBe(false);
    expect(entries[0].skippedReason).toContain('Casual question');
  });

  it('does not log secrets', () => {
    logModelAttempt({
      route: 'primary_model',
      modelProvider: 'openrouter',
      modelName: 'gpt-4o-mini',
      promptType: 'strategy',
      estimatedInputTokens: 500,
      estimatedOutputTokens: 200,
      contextSources: ['supabase_summary'],
      wasModelCalled: true,
      skippedReason: '',
      fallbackUsed: '',
      costEstimateAvailable: false,
      error: '',
      durationMs: 1200,
    });

    const entries = getUsageEntries();
    const raw = JSON.stringify(entries);
    expect(raw).not.toContain('sk-');
    expect(raw).not.toContain('api_key');
    expect(raw).not.toContain('service_role');
  });

  it('calculates total tokens', () => {
    logModelAttempt({
      route: 'primary_model',
      modelProvider: 'openrouter',
      modelName: 'gpt-4o-mini',
      promptType: 'strategy',
      estimatedInputTokens: 1000,
      estimatedOutputTokens: 500,
      contextSources: [],
      wasModelCalled: true,
      skippedReason: '',
      fallbackUsed: '',
      costEstimateAvailable: false,
      error: '',
      durationMs: 1000,
    });

    logModelAttempt({
      route: 'cheap_model',
      modelProvider: 'openrouter',
      modelName: 'gpt-4o-mini',
      promptType: 'rewrite',
      estimatedInputTokens: 200,
      estimatedOutputTokens: 100,
      contextSources: [],
      wasModelCalled: true,
      skippedReason: '',
      fallbackUsed: '',
      costEstimateAvailable: false,
      error: '',
      durationMs: 500,
    });

    const totals = getTotalTokensUsed();
    expect(totals.input).toBe(1200);
    expect(totals.output).toBe(600);
    expect(totals.calls).toBe(2);
  });

  it('answers what model did you use', () => {
    logModelAttempt({
      route: 'primary_model',
      modelProvider: 'openrouter',
      modelName: 'gpt-4o-mini',
      promptType: 'strategy',
      estimatedInputTokens: 500,
      estimatedOutputTokens: 200,
      contextSources: [],
      wasModelCalled: true,
      skippedReason: '',
      fallbackUsed: '',
      costEstimateAvailable: false,
      error: '',
      durationMs: 1000,
    });

    const answer = getModelActivityAnswer();
    expect(answer).toContain('openrouter');
    expect(answer).toContain('gpt-4o-mini');
  });

  it('answers no calls when empty', () => {
    const answer = getModelActivityAnswer();
    expect(answer).toContain('No model calls');
  });

  it('recent usage summary shows entries', () => {
    logModelSkipped('Casual', 'local_answer');
    logModelAttempt({
      route: 'cheap_model',
      modelProvider: 'supabase_edge_function',
      modelName: 'hermes-chat',
      promptType: 'rewrite',
      estimatedInputTokens: 100,
      estimatedOutputTokens: 50,
      contextSources: [],
      wasModelCalled: true,
      skippedReason: '',
      fallbackUsed: '',
      costEstimateAvailable: false,
      error: '',
      durationMs: 300,
    });

    const summary = getRecentUsageSummary(5);
    expect(summary).toContain('no_model');
    expect(summary).toContain('cheap_model');
  });

  it('clears usage log', () => {
    logModelSkipped('test', 'test');
    expect(getUsageEntries().length).toBe(1);
    clearUsageLog();
    expect(getUsageEntries().length).toBe(0);
  });
});
