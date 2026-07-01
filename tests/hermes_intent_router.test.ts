import { beforeEach, describe, expect, it } from 'vitest';
import { classifyIntent, hermesResponseRouter, normalizeHermesText } from '../src/lib/hermesResponseRouter';
import { setLastReferencedEntity } from '../src/lib/hermesEntityResolver';

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
    expect(result.text).toContain('You asked: “can you find out.”');
    expect(result.text).toContain('Reports page context');
    expect(result.text).toMatch(/local bundled context.*local activity memory/i);
    expect(result.clarificationQuestion).toMatch(/Which source/i);
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
