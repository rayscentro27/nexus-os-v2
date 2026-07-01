import { beforeEach, describe, expect, it } from 'vitest';
import { classifyIntent, hermesResponseRouter, normalizeHermesText } from '../src/lib/hermesResponseRouter';
import { setLastReferencedEntity, setLastHermesListedRecords } from '../src/lib/hermesEntityResolver';

const tradingItems = [
  { type: 'strategy', title: 'Half Trend Forex Strategy', status: 'Backtested · paper/demo only', dataSource: 'local_static' as const },
  { type: 'strategy', title: 'Options Income Idea', status: 'Needs Review · paper/demo only', dataSource: 'local_static' as const },
  { type: 'strategy', title: 'Crypto Breakout Model', status: 'Paper Demo', dataSource: 'local_static' as const },
];

describe('Hermes intent router coverage', () => {
  beforeEach(() => setLastReferencedEntity(null));

  it('normalizes whitespace, punctuation, curly apostrophes, and missing apostrophes', () => {
    expect(normalizeHermesText('  What   is TODAY’S date?! ')).toBe("what is today's date");
    expect(normalizeHermesText('what is todays date')).toBe("what is today's date");
  });

  it.each([
    'what is todays date', "what is today's date", 'what is today’s date', 'what date is it',
    'what day is it', 'what day are we on', 'what is the date', 'todays date', 'today date',
    'what time is it', 'current time', 'time now',
  ])('classifies %s as date_time', phrase => expect(classifyIntent(phrase)).toBe('date_time'));

  it.each(['good morning', 'good afternoon', 'good evening', 'good night', 'morning', 'afternoon', 'evening'])
    ('classifies %s as greeting', phrase => expect(classifyIntent(phrase)).toBe('greeting'));

  it.each(['this evening', 'tonight', 'tomorrow morning', 'later today', 'next friday', 'in 2 hours', 'schedule something for this evening'])
    ('classifies %s as scheduling', phrase => expect(classifyIntent(phrase)).toBe('scheduling'));

  it('returns browser date/time context rather than fallback', () => {
    for (const phrase of ['what is todays date', 'what is today’s date', 'what day is it', 'what time is it']) {
      const result = hermesResponseRouter({ message: phrase, pageId: 'hermes' });
      expect(result.source).toBe('time_context');
      expect(result.text).toMatch(/\d|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday/);
      expect(result.text).not.toMatch(/not sure what you're asking/i);
    }
  });

  it('resolves the first visible Trading strategy and its paper status', () => {
    const result = hermesResponseRouter({ message: 'tell me about the first strategy on this page', pageId: 'trading', visibleItems: tradingItems });
    expect(result.text).toMatch(/Half Trend Forex Strategy/);
    expect(result.text).toMatch(/paper|demo/i);
  });

  it('clarifies first strategy on Hermes and ambiguous Trading comparison', () => {
    const absent = hermesResponseRouter({ message: 'tell me about the first strategy on this page', pageId: 'hermes' });
    expect(absent.text).toMatch(/no strategy visible.*Hermes Workroom/i);
    hermesResponseRouter({ message: 'tell me about the first strategy on this page', pageId: 'trading', visibleItems: tradingItems });
    const compare = hermesResponseRouter({ message: 'compare that strategy with another trading strategy', pageId: 'trading', visibleItems: tradingItems });
    expect(compare.text).toMatch(/Half Trend Forex Strategy/);
    expect(compare.needsClarification).toBe(true);
  });

  it('uses a request-specific, source-aware fallback', () => {
    const result = hermesResponseRouter({ message: 'can you find out', pageId: 'reports' });
    expect(result.text).toContain('can you find out');
    expect(result.text).toContain('Reports page context');
    expect(result.text).toMatch(/local bundled context|live Supabase data/i);
    expect(result.needsClarification).toBe(true);
  });

  it.each([
    ['what is the status of our system', /Operating Activation Master.*static/is],
    ['is there anything we can improve', /Global Blocker Matrix.*approval-gated/is],
    ['how do we make money today', /\$97 Credit & Funding Readiness Review.*approval-gated/is],
    ['what is the best business opportunity we have right now', /\$97 readiness review.*approval-gated/is],
    ['what does this revenue dashboard mean and what should I do next', /Confirmed revenue is \$0.*Static build-time report snapshot/is],
  ])('uses safe context for %s', (message, expected) => {
    const result = hermesResponseRouter({ message, pageId: message.includes('dashboard') ? 'reports' : 'hermes' });
    expect(result.text).toMatch(expected);
    expect(result.source).not.toBe('honest_fallback');
  });

  it.each(['send the email', 'charge the customer', 'publish this post', 'place a live trade', 'insert this real client'])
    ('refuses direct execution for %s', message => {
      const result = hermesResponseRouter({ message, pageId: 'hermes' });
      expect(result.questionType).toBe('execution');
      expect(result.text).toMatch(/can't execute.*directly/is);
      expect(result.text).toMatch(/approval|safe server-side workflow|Trading workflow/i);
    });
});

describe('safe backend context adapter', () => {
  it('returns a typed static report result without claiming live backend access', async () => {
    const { getHermesContext, isBackendAvailable, isWebSearchAvailable } = await import('../src/lib/hermesBackendContextAdapter');
    const result = getHermesContext('revenue', { type: 'selected_report', selectedReport: 'Revenue Dashboard' });
    expect(result.ok).toBe(true);
    expect(result.sourceType).toBe('report');
    expect(result.liveData).toBe(false);
    expect(result.requiresApprovalForExecution).toBe(true);
    expect(isBackendAvailable()).toBe(false);
    expect(isWebSearchAvailable()).toBe(false);
  });
});

describe('research crash fix — live data normalization', () => {
  it('safeStr handles null, undefined, numbers, objects', async () => {
    const { safeStr, safeNum, safeReplace } = await import('../src/lib/liveDataLoader');
    expect(safeStr(null)).toBe('');
    expect(safeStr(undefined)).toBe('');
    expect(safeStr(42)).toBe('42');
    expect(safeStr({ a: 1 })).toContain('a');
    expect(safeStr('hello', 'fallback')).toBe('hello');
    expect(safeNum(null)).toBe(0);
    expect(safeNum('abc')).toBe(0);
    expect(safeNum(42)).toBe(42);
    expect(safeReplace(undefined, /_/g, ' ')).toBe('');
    expect(safeReplace(null, /_/g, ' ')).toBe('');
    expect(safeReplace('hello_world', /_/g, ' ')).toBe('hello world');
  });

  it('normalizeResearchRow maps Supabase columns to UI shape', async () => {
    const { normalizeResearchRow } = await import('../src/lib/liveDataLoader');
    const row = {
      id: 'abc-123',
      title: 'Test Article',
      source_type: 'article',
      confidence: 85,
      why_it_matters: 'Important for credit readiness',
      snippet: 'A brief snippet',
      metadata: { lane: 'credit_readiness', type: 'article', score: 85, status: 'scored', nextAction: 'Review', convertOptions: ['opportunity'] },
    };
    const normalized = normalizeResearchRow(row, 0);
    expect(normalized.title).toBe('Test Article');
    expect(normalized.lane).toBe('credit_readiness');
    expect(normalized.score).toBe(85);
    expect(normalized.reason).toBe('Important for credit readiness');
    expect(normalized.status).toBe('scored');
    expect(normalized.nextAction).toBe('Review');
    expect(normalized.convertOptions).toEqual(['opportunity']);
    expect(normalized.raw).toBe(row);
  });

  it('normalizeResearchRow handles missing fields safely', async () => {
    const { normalizeResearchRow } = await import('../src/lib/liveDataLoader');
    const sparseRow = { id: 'x', title: null, source_type: null, confidence: null, metadata: null };
    const normalized = normalizeResearchRow(sparseRow, 0);
    expect(normalized.title).toBe('Untitled Research');
    expect(normalized.lane).toBe('research');
    expect(normalized.score).toBe(50);
    expect(normalized.status).toBe('scored');
    expect(normalized.reason).toBeTruthy();
  });

  it('normalizeBusinessRow maps Supabase columns to UI shape', async () => {
    const { normalizeBusinessRow } = await import('../src/lib/liveDataLoader');
    const row = {
      id: 'biz-1',
      title: 'Credit Assessment',
      summary: 'A summary',
      score: 80,
      status: 'open',
      category: 'credit',
      source: 'supabase',
    };
    const normalized = normalizeBusinessRow(row, 0);
    expect(normalized.title).toBe('Credit Assessment');
    expect(normalized.score).toBe(80);
    expect(normalized.category).toBe('credit');
  });

  it('normalizeMonetizationRow maps columns safely', async () => {
    const { normalizeMonetizationRow } = await import('../src/lib/liveDataLoader');
    const row = { id: 'm1', title: '$97 Review', status: 'open', overall_score: 90, money_angle: 'Test revenue' };
    const normalized = normalizeMonetizationRow(row, 0);
    expect(normalized.title).toBe('$97 Review');
    expect(normalized.score).toBe(90);
    expect(normalized.moneyAngle).toBe('Test revenue');
  });

  it('normalizeClientRow maps columns safely', async () => {
    const { normalizeClientRow } = await import('../src/lib/liveDataLoader');
    const row = { id: 'c1', client_label: 'Julius', current_stage: 'document_prep', progress_percentage: 72 };
    const normalized = normalizeClientRow(row, 0);
    expect(normalized.title).toBe('Julius');
    expect(normalized.status).toBe('document_prep');
    expect(normalized.score).toBe(72);
  });

  it('normalizeRayReviewRow maps columns safely', async () => {
    const { normalizeRayReviewRow } = await import('../src/lib/liveDataLoader');
    const row = { id: 'r1', task_type: 'ray_review_item', status: 'requested', payload: { title: 'Review social draft', summary: 'Check draft' } };
    const normalized = normalizeRayReviewRow(row, 0);
    expect(normalized.title).toBe('Review social draft');
    expect(normalized.status).toBe('requested');
    expect(normalized.type).toBe('ray_review_item');
  });
});

describe('Hermes entity resolution — first one / review the first', () => {
  beforeEach(() => {
    setLastReferencedEntity(null);
    setLastHermesListedRecords([]);
  });

  const liveItems = [
    { type: 'opportunity', title: 'Credit Assessment Service', status: 'active', dataSource: 'supabase' as const },
    { type: 'opportunity', title: 'Business Credit Builder', status: 'active', dataSource: 'supabase' as const },
    { type: 'opportunity', title: 'Funding Prep Sprint', status: 'active', dataSource: 'supabase' as const },
  ];

  it('"the first one" resolves to first item from listed records', () => {
    setLastHermesListedRecords(liveItems);
    const result = hermesResponseRouter({ message: 'the first one', pageId: 'opportunity' });
    expect(result.questionType).toBe('entity_question');
    expect(result.text).toContain('Credit Assessment Service');
    expect(result.source).toBe('entity_resolution');
  });

  it('"review the first" resolves to first item', () => {
    setLastHermesListedRecords(liveItems);
    const result = hermesResponseRouter({ message: 'review the first', pageId: 'opportunity' });
    expect(result.questionType).toBe('entity_question');
    expect(result.text).toContain('Credit Assessment Service');
  });

  it('"the second one" resolves to second item', () => {
    setLastHermesListedRecords(liveItems);
    const result = hermesResponseRouter({ message: 'the second one', pageId: 'opportunity' });
    expect(result.questionType).toBe('entity_question');
    expect(result.text).toContain('Business Credit Builder');
  });

  it('"the last one" resolves to last item', () => {
    setLastHermesListedRecords(liveItems);
    const result = hermesResponseRouter({ message: 'the last one', pageId: 'opportunity' });
    expect(result.questionType).toBe('entity_question');
    expect(result.text).toContain('Funding Prep Sprint');
  });

  it('entity resolution includes Live Supabase source label', () => {
    setLastHermesListedRecords(liveItems);
    const result = hermesResponseRouter({ message: 'the first one', pageId: 'opportunity' });
    expect(result.text).toMatch(/Live Supabase/i);
  });

  it('asks clarification when no listed records and no visible items', () => {
    const result = hermesResponseRouter({ message: 'the first one', pageId: 'opportunity' });
    expect(result.needsClarification).toBe(true);
  });
});

describe('Hermes connection status answers', () => {
  it('"are you connected to Supabase" gives accurate status', () => {
    const result = hermesResponseRouter({ message: 'are you connected to Supabase', pageId: 'hermes' });
    expect(result.questionType).toBe('backend_query');
    expect(result.text).toMatch(/Supabase/i);
    expect(result.text).not.toMatch(/I do not have live Supabase/i);
  });

  it('"are you connected to the internet" says no web search', () => {
    const result = hermesResponseRouter({ message: 'are you connected to the internet', pageId: 'hermes' });
    expect(result.questionType).toBe('backend_query');
    expect(result.text).toMatch(/web search|internet/i);
    expect(result.text).not.toMatch(/I do not have live Supabase/i);
  });

  it('"are you connected to social media" gives verified/unverified status', () => {
    const result = hermesResponseRouter({ message: 'are you connected to social media accounts', pageId: 'hermes' });
    expect(result.questionType).toBe('backend_query');
    expect(result.text).toMatch(/social media|not verified/i);
    expect(result.text).not.toMatch(/I do not have live Supabase/i);
  });

  it('"are you connected to a live model" distinguishes model vs router', () => {
    const result = hermesResponseRouter({ message: 'are you connected to a live model', pageId: 'hermes' });
    expect(result.questionType).toBe('backend_query');
    expect(result.text).toMatch(/model|router/i);
    expect(result.text).not.toMatch(/I do not have live Supabase/i);
  });
});

describe('Hermes casual conversation fallback', () => {
  it('"what is your favorite sport" gets natural non-human answer', () => {
    const result = hermesResponseRouter({ message: 'what is your favorite sport', pageId: 'hermes' });
    expect(result.questionType).toBe('casual');
    expect(result.text).toMatch(/basketball|strategy/i);
    expect(result.text).not.toMatch(/operating context/i);
  });

  it('"how are you" gives natural response', () => {
    const result = hermesResponseRouter({ message: 'how are you', pageId: 'hermes' });
    expect(result.questionType).toBe('casual');
    expect(result.text).toMatch(/running|operational/i);
  });

  it('"are you real" identifies as Hermes', () => {
    const result = hermesResponseRouter({ message: 'are you real', pageId: 'hermes' });
    expect(result.questionType).toBe('casual');
    expect(result.text).toMatch(/Hermes|advisor/i);
  });
});

describe('Hermes scheduling intent fix', () => {
  it('"schedule a report for next Wednesday" does not say today', () => {
    const result = hermesResponseRouter({ message: 'can you schedule a report for next Wednesday', pageId: 'hermes' });
    expect(result.questionType).toBe('scheduling');
    expect(result.text).not.toMatch(/between .* today/i);
    expect(result.text).toMatch(/Wednesday|Ray Review|task request/i);
  });

  it('scheduling without time asks for clarification', () => {
    const result = hermesResponseRouter({ message: 'schedule something for next Friday', pageId: 'hermes' });
    expect(result.questionType).toBe('scheduling');
    expect(result.needsClarification).toBe(false);
  });
});
