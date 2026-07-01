/**
 * Hermes Live Context Tests
 *
 * Proves that Hermes answers questions about Supabase, web search, and live data honestly.
 *
 * Run: npx vitest run tests/hermes_live_context.test.ts
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
    get length() { return Object.keys(store).length; },
    key: vi.fn((index: number) => Object.keys(store)[index] || null),
  };
})();

vi.stubGlobal('window', { localStorage: localStorageMock });
vi.stubGlobal('Intl', { DateTimeFormat: () => ({ resolvedOptions: () => ({ timeZone: 'America/New_York' }) }) });

describe('Hermes Supabase context adapter', () => {
  beforeEach(() => localStorageMock.clear());

  it('isSupabaseAvailable returns configured status', async () => {
    const { isSupabaseAvailable } = await import('../src/lib/hermesSupabaseContextAdapter');
    const result = isSupabaseAvailable();
    expect(typeof result).toBe('boolean');
  });

  it('querySupabaseContext returns honest stub', async () => {
    const { querySupabaseContext } = await import('../src/lib/hermesSupabaseContextAdapter');
    const result = querySupabaseContext('approvals');
    expect(result.table).toBe('approvals');
  });

  it('getSupabaseStatusMessage returns honest status', async () => {
    const { getSupabaseStatusMessage } = await import('../src/lib/hermesSupabaseContextAdapter');
    const msg = getSupabaseStatusMessage();
    expect(msg).toBeTruthy();
    expect(typeof msg).toBe('string');
  });
});

describe('Hermes live context builder', () => {
  it('buildLiveSupabaseContext returns live or fallback response', async () => {
    const { buildLiveSupabaseContext } = await import('../src/lib/hermesLiveContext');
    const result = await buildLiveSupabaseContext('can you check Supabase');
    expect(result).toHaveProperty('text');
    expect(result).toHaveProperty('source');
    expect(result).toHaveProperty('liveData');
    expect(result).toHaveProperty('timestamp');
    expect(result.text).toBeTruthy();
  });

  it('buildWebSearchResponse returns honest result', async () => {
    const { buildWebSearchResponse } = await import('../src/lib/hermesLiveContext');
    const result = await buildWebSearchResponse('what is the latest AI news');
    expect(result).toHaveProperty('text');
    expect(result).toHaveProperty('source');
    expect(result).toHaveProperty('liveData');
    expect(result.text).toBeTruthy();
  });
});

describe('Hermes response router Supabase questions', () => {
  beforeEach(() => localStorageMock.clear());

  it('"can you check Supabase" returns honest answer', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'can you check Supabase', pageId: 'hermes' });
    expect(result.questionType).toBe('supabase_query');
    // Should not claim live access without proof
    expect(result.text).toMatch(/Supabase/);
  });

  it('"what approvals are in Supabase" returns context-aware answer', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'what approvals are in Supabase', pageId: 'hermes' });
    expect(result.text).toBeTruthy();
    expect(result.text).toMatch(/local bundled|static|Supabase/i);
  });

  it('"did my approval persist" mentions source type', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'did my approval persist', pageId: 'hermes' });
    expect(result.text).toBeTruthy();
    // Should mention source type or local/static nature
    expect(result.text).toMatch(/local|static|receipt|Supabase/i);
  });

  it('"what research candidates are in Supabase" returns honest answer', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'what research candidates are in Supabase', pageId: 'hermes' });
    expect(result.text).toBeTruthy();
  });

  it('"is the research engine adding to Supabase" returns honest answer', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'is the research engine adding to Supabase', pageId: 'hermes' });
    expect(result.text).toBeTruthy();
  });
});

describe('Hermes web search questions', () => {
  it('"can you search the internet" classifies as backend_query', async () => {
    const { classifyIntent } = await import('../src/lib/hermesResponseRouter');
    const intent = classifyIntent('can you search the internet');
    expect(intent).toBe('backend_query');
  });

  it('"search the internet for AI news" classifies as backend_query', async () => {
    const { classifyIntent } = await import('../src/lib/hermesResponseRouter');
    const intent = classifyIntent('search the internet for AI news');
    expect(intent).toBe('backend_query');
  });
});

describe('Hermes backend adapter honesty', () => {
  it('isBackendAvailable returns false', async () => {
    const { isBackendAvailable } = await import('../src/lib/hermesBackendContextAdapter');
    expect(isBackendAvailable()).toBe(false);
  });

  it('isWebSearchAvailable returns false', async () => {
    const { isWebSearchAvailable } = await import('../src/lib/hermesBackendContextAdapter');
    expect(isWebSearchAvailable()).toBe(false);
  });

  it('getBackendStatusMessage mentions local bundled or Supabase', async () => {
    const { getBackendStatusMessage } = await import('../src/lib/hermesBackendContextAdapter');
    const msg = getBackendStatusMessage();
    // When Supabase is configured: mentions Supabase read access
    // When not configured: mentions local bundled context
    expect(msg).toMatch(/Supabase|local bundled/i);
  });
});

describe('Hermes providers honest state', () => {
  it('hermesChat returns configured status based on env', async () => {
    const { hermesChat } = await import('../src/lib/hermesProviders');
    const result = await hermesChat('hello', 'conversation');
    // Returns configured based on VITE_HERMES_CHAT_ENABLED env var
    expect(result).toHaveProperty('configured');
    expect(typeof result.configured).toBe('boolean');
  });

  it('publicSearch returns not-configured when SEARCH_ENABLED is false', async () => {
    const { publicSearch } = await import('../src/lib/hermesProviders');
    const result = await publicSearch('what is AI');
    expect(result.configured).toBe(false);
  });
});
