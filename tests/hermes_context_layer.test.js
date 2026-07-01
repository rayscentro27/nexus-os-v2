/**
 * Tests for Hermes CEO Context Layer infrastructure.
 *
 * Run: node --experimental-vm-modules node_modules/.bin/jest tests/hermes_context_layer.test.js
 * Or: npx vitest run tests/hermes_context_layer.test.js
 *
 * These tests verify the core infrastructure without requiring a browser.
 * They test the pure functions and localStorage mocking.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock localStorage
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: vi.fn(key => store[key] || null),
    setItem: vi.fn((key, value) => { store[key] = value; }),
    removeItem: vi.fn(key => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
    get length() { return Object.keys(store).length; },
    key: vi.fn(index => Object.keys(store)[index] || null),
  };
})();

// Mock window.localStorage
vi.stubGlobal('window', { localStorage: localStorageMock });
vi.stubGlobal('Intl', { DateTimeFormat: () => ({ resolvedOptions: () => ({ timeZone: 'America/New_York' }) }) });

describe('Hermes Time Context', () => {
  it('getTimeContext returns valid time context', async () => {
    const { getTimeContext } = await import('../src/lib/hermesTimeContext');
    const ctx = getTimeContext();

    expect(ctx.source).toBe('browser');
    expect(ctx.serverTimeAvailable).toBe(false);
    expect(ctx.browserTime).toBeInstanceOf(Date);
    expect(ctx.isoTimestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(ctx.formattedDate).toBeTruthy();
    expect(ctx.formattedTime).toBeTruthy();
    expect(ctx.dayOfWeek).toBeTruthy();
    expect(ctx.timezone).toBeTruthy();
    expect(['morning', 'afternoon', 'evening', 'night']).toContain(ctx.timeOfDay);
  });

  it('detectTimeIntent detects time questions', async () => {
    const { detectTimeIntent } = await import('../src/lib/hermesTimeContext');

    expect(detectTimeIntent('what day is it?').isTimeQuestion).toBe(true);
    expect(detectTimeIntent('what time is it?').isTimeQuestion).toBe(true);
    expect(detectTimeIntent('what is today?').isTimeQuestion).toBe(true);
    expect(detectTimeIntent('hello').isTimeQuestion).toBe(false);
  });

  it('detectTimeIntent detects scheduling phrases', async () => {
    const { detectTimeIntent } = await import('../src/lib/hermesTimeContext');

    expect(detectTimeIntent('schedule this for tonight').isSchedulingPhrase).toBe(true);
    expect(detectTimeIntent('set up a task for tomorrow').isSchedulingPhrase).toBe(true);
    expect(detectTimeIntent('remind me in 2 hours').isSchedulingPhrase).toBe(true);
    expect(detectTimeIntent('hello').isSchedulingPhrase).toBe(false);
  });

  it('resolveRelativeTime resolves "today"', async () => {
    const { resolveRelativeTime } = await import('../src/lib/hermesTimeContext');
    const result = resolveRelativeTime('today');

    expect(result).not.toBeNull();
    expect(result.label).toBe('today');
    expect(result.start).toBeInstanceOf(Date);
    expect(result.end).toBeInstanceOf(Date);
  });

  it('resolveRelativeTime resolves "tomorrow"', async () => {
    const { resolveRelativeTime } = await import('../src/lib/hermesTimeContext');
    const result = resolveRelativeTime('tomorrow');

    expect(result).not.toBeNull();
    expect(result.label).toBe('tomorrow');
  });

  it('resolveRelativeTime resolves "yesterday"', async () => {
    const { resolveRelativeTime } = await import('../src/lib/hermesTimeContext');
    const result = resolveRelativeTime('yesterday');

    expect(result).not.toBeNull();
    expect(result.label).toBe('yesterday');
  });

  it('resolveRelativeTime returns null for unrecognized phrases', async () => {
    const { resolveRelativeTime } = await import('../src/lib/hermesTimeContext');
    expect(resolveRelativeTime('xyz')).toBeNull();
  });
});

describe('Hermes Entity Resolver', () => {
  it('resolves "this" from selected item', async () => {
    const { resolveEntity } = await import('../src/lib/hermesEntityResolver');
    const pageContext = {
      route: '/#trading',
      pageId: 'trading',
      pageTitle: 'Trading',
      activeTab: null,
      selectedItem: { type: 'strategy', title: 'Momentum Alpha', status: 'active', dataSource: 'local_static' },
      visibleItems: [],
      availableActions: [],
      gatedActions: [],
      blockedActions: [],
      pageDataSource: 'local_static',
      staleStatus: 'static',
    };

    const result = resolveEntity('analyze this', pageContext);
    expect(result.item?.title).toBe('Momentum Alpha');
    expect(result.confidence).toBe('high');
    expect(result.clarificationNeeded).toBe(false);
  });

  it('resolves "first strategy" from visible items', async () => {
    const { resolveEntity } = await import('../src/lib/hermesEntityResolver');
    const pageContext = {
      route: '/#trading',
      pageId: 'trading',
      pageTitle: 'Trading',
      activeTab: null,
      selectedItem: null,
      visibleItems: [
        { type: 'strategy', title: 'Momentum Alpha', status: 'active', dataSource: 'local_static' },
        { type: 'strategy', title: 'Mean Reversion', status: 'pending', dataSource: 'local_static' },
      ],
      availableActions: [],
      gatedActions: [],
      blockedActions: [],
      pageDataSource: 'local_static',
      staleStatus: 'static',
    };

    const result = resolveEntity('show me the first strategy', pageContext);
    expect(result.item?.title).toBe('Momentum Alpha');
    expect(result.confidence).toBe('high');
  });

  it('returns clarification for ambiguous references', async () => {
    const { resolveEntity, setLastReferencedEntity } = await import('../src/lib/hermesEntityResolver');
    setLastReferencedEntity(null);

    const pageContext = {
      route: '/#trading',
      pageId: 'trading',
      pageTitle: 'Trading',
      activeTab: null,
      selectedItem: null,
      visibleItems: [],
      availableActions: [],
      gatedActions: [],
      blockedActions: [],
      pageDataSource: 'local_static',
      staleStatus: 'static',
    };

    const result = resolveEntity('this', pageContext);
    expect(result.clarificationNeeded).toBe(true);
    expect(result.confidence).toBe('low');
  });
});

describe('Hermes Activity Journal', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('records and retrieves activity events', async () => {
    const { recordActivity, getTodayEvents } = await import('../src/lib/hermesActivityJournal');

    const event = recordActivity({
      source: 'test',
      pageId: 'trading',
      route: '/#trading',
      eventType: 'page_view',
      title: 'Viewed trading page',
      summary: 'Navigated to trading',
      entities: ['trading'],
      status: 'completed',
      importance: 'low',
      dataSource: 'local_static',
      safetyLevel: 'safe',
    });

    expect(event.id).toMatch(/^act-/);
    expect(event.timestamp).toBeTruthy();

    const todayEvents = getTodayEvents();
    expect(todayEvents.length).toBeGreaterThanOrEqual(1);
  });

  it('clears journal', async () => {
    const { recordActivity, clearJournal, getAllEvents } = await import('../src/lib/hermesActivityJournal');

    recordActivity({
      source: 'test',
      pageId: 'trading',
      route: '/#trading',
      eventType: 'page_view',
      title: 'Test event',
      summary: 'Test',
      entities: [],
      status: 'completed',
      importance: 'low',
      dataSource: 'local_static',
      safetyLevel: 'safe',
    });

    expect(getAllEvents().length).toBeGreaterThan(0);
    clearJournal();
    expect(getAllEvents().length).toBe(0);
  });
});

describe('Hermes Source Hints / Learning', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('detects learning instructions', async () => {
    const { detectLearningInstruction } = await import('../src/lib/hermesSourceHints');

    const result1 = detectLearningInstruction('remember that when I ask about trading, show me the top strategy first');
    expect(result1.isLearning).toBe(true);
    expect(result1.hint?.memoryType).toBe('preference');

    const result2 = detectLearningInstruction('from now on, always summarize blockers first');
    expect(result2.isLearning).toBe(true);
    expect(result2.hint?.memoryType).toBe('recurring_instruction');

    const result3 = detectLearningInstruction('hello');
    expect(result3.isLearning).toBe(false);
  });

  it('stores and finds hints', async () => {
    const { storeHint, findMatchingHints } = await import('../src/lib/hermesSourceHints');

    storeHint({
      memoryType: 'recurring_instruction',
      instruction: 'from now on, always show blockers first',
      triggerPhrase: 'blockers',
      source: 'user_instruction',
      confidence: 1.0,
      safetyLevel: 'safe',
    });

    const matches = findMatchingHints('show me the blockers');
    expect(matches.length).toBe(1);
    expect(matches[0].instruction).toBe('from now on, always show blockers first');
  });
});

describe('Hermes Memory Query', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('queries memory for today', async () => {
    const { queryMemory } = await import('../src/lib/hermesMemoryQuery');
    const result = queryMemory('today');

    expect(result.timeRangeUsed).toBe('today');
    expect(result.events).toBeDefined();
    expect(result.summary).toBeTruthy();
  });

  it('queries memory for yesterday', async () => {
    const { queryMemory } = await import('../src/lib/hermesMemoryQuery');
    const result = queryMemory('yesterday');

    expect(result.timeRangeUsed).toBe('yesterday');
    expect(result.events).toBeDefined();
  });
});

describe('Hermes Response Router', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('routes greeting questions', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'hello' });

    expect(result.questionType).toBe('greeting');
    expect(result.text).toBeTruthy();
    expect(result.source).toBe('time_context');
  });

  it('routes date/time questions', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'what day is it?' });

    expect(result.questionType).toBe('date_time');
    expect(result.text).toMatch(/Today is|It's/);
  });

  it('routes entity questions', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({
      message: 'show me the first strategy',
      pageId: 'trading',
      visibleItems: [
        { type: 'strategy', title: 'Momentum Alpha', status: 'active', dataSource: 'local_static' },
      ],
    });

    expect(result.questionType).toBe('entity_question');
    expect(result.text).toContain('Momentum Alpha');
  });

  it('routes memory questions', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'what did we work on today?' });

    expect(result.questionType).toBe('memory_history');
    expect(result.text).toBeTruthy();
  });

  it('routes learning instructions', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'remember that I prefer concise answers' });

    expect(result.questionType).toBe('learning_instruction');
    expect(result.text).toContain('remember');
  });

  it('routes unclear questions with honest fallback', async () => {
    const { hermesResponseRouter } = await import('../src/lib/hermesResponseRouter');
    const result = hermesResponseRouter({ message: 'asdklfj' });

    expect(result.questionType).toBe('unclear');
    expect(result.text).toContain('local bundled context');
    expect(result.needsClarification).toBe(true);
  });
});

describe('Hermes Page Context Bridge', () => {
  it('builds page context from pageId', async () => {
    const { buildPageContext } = await import('../src/lib/hermesContextBridge');
    const ctx = buildPageContext('trading');

    expect(ctx.pageId).toBe('trading');
    expect(ctx.pageTitle).toBe('Trading Demo');
    expect(ctx.pageDataSource).toBe('local_static');
    expect(ctx.staleStatus).toBe('static');
    expect(ctx.blockedActions).toContain('live trading');
  });
});

describe('Hermes Supabase Context Adapter', () => {
  it('returns honest status', async () => {
    const { querySupabaseContext, isSupabaseAvailable } = await import('../src/lib/hermesSupabaseContextAdapter');

    // isSupabaseAvailable returns isSupabaseConfigured (sync check)
    const available = isSupabaseAvailable();
    expect(typeof available).toBe('boolean');

    const result = querySupabaseContext('strategies');
    expect(result.table).toBe('strategies');
  });
});

describe('Hermes Backend Context Adapter', () => {
  it('returns honest stub', async () => {
    const { isBackendAvailable, getBackendStatusMessage } = await import('../src/lib/hermesBackendContextAdapter');

    expect(isBackendAvailable()).toBe(false);
    const msg = getBackendStatusMessage();
    // When Supabase is configured: mentions Supabase read access
    // When not configured: mentions local bundled context
    expect(msg).toMatch(/Supabase|local bundled/i);
  });
});
