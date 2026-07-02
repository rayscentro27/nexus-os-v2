import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { resetConversationState } from '../src/lib/hermesConversationState';
import { clearRoutingTraces, getRoutingTraces } from '../src/lib/hermesRoutingTrace';
import { answerTradingQuestion } from '../src/lib/hermesTradingReasoner';
import { answerRevenueStrategy, isRevenueStrategyQuestion } from '../src/lib/hermesRevenueReasoner';

class MemoryStorage implements Storage {
  private values = new Map<string, string>();
  get length() { return this.values.size; }
  clear() { this.values.clear(); }
  getItem(key: string) { return this.values.get(key) ?? null; }
  key(index: number) { return [...this.values.keys()][index] ?? null; }
  removeItem(key: string) { this.values.delete(key); }
  setItem(key: string, value: string) { this.values.set(key, value); }
}

describe('real Hermes transcript regression', () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, 'window', { value: { localStorage: new MemoryStorage() }, configurable: true });
    resetConversationState();
    clearRoutingTraces();
  });

  it('routes the exact failed transcript through trace, trading, and revenue handlers', async () => {
    const opening = await handleHermesMessage({ message: 'What trading strategy do you recommend', surface: 'full_workroom' });
    expect(opening.diagnostics.answerBuilder).toBe('trading_evidence_recommendation');

    const implicit = await handleHermesMessage({ message: 'but do you have a strategy you can recommend', surface: 'full_workroom' });
    expect(implicit.diagnostics.domain).toMatchObject({ domain: 'trading' });
    expect(implicit.text).toContain('cannot honestly recommend');
    expect(implicit.text).not.toContain('I detected the general domain');

    const explicit = await handleHermesMessage({ message: 'but do you have a trading strategy you recommend', surface: 'full_workroom' });
    expect(explicit.diagnostics.answerBuilder).toBe('trading_evidence_recommendation');

    const listed = await handleHermesMessage({ message: 'so what strategies are in the trading lab', surface: 'full_workroom' });
    expect(listed.diagnostics.answerBuilder).toBe('trading_strategy_list');
    expect(listed.text).toContain('Half Trend Forex Strategy');
    expect(listed.text).toContain('AI Market Watcher');

    const source = await handleHermesMessage({ message: 'where did you get your last response from', surface: 'full_workroom' });
    expect(source.diagnostics.answerBuilder).toBe('trace_question_handler');
    expect(source.text).toContain('Domain: trading');
    expect(source.text).not.toContain('Funding Application Prep Sprint');

    const domain = await handleHermesMessage({ message: 'what domain did you detect', surface: 'full_workroom' });
    expect(domain.text).toContain('trading');

    const generalSource = await handleHermesMessage({ message: 'where are you getting the answer to your questions', surface: 'full_workroom' });
    expect(generalSource.text).toContain('routing record');

    const supabase = await handleHermesMessage({ message: 'are you using supabase', surface: 'full_workroom' });
    expect(supabase.text).toContain('For my last answer: no');
    expect(supabase.text).toContain('In general:');
    expect(supabase.text).not.toContain('live AI model');

    const reasoning = await handleHermesMessage({ message: 'so are you using strategic reasoning', surface: 'full_workroom' });
    expect(reasoning.text).toContain('local_reasoning');
    expect(reasoning.text).toContain('Model used: no');

    const money = await handleHermesMessage({ message: 'what is the most money we can make of the next 30 says', surface: 'full_workroom' });
    expect(money.diagnostics.answerBuilder).toBe('revenue_30_day_reasoner');
    expect(money.text).toContain('$3,425');
    expect(money.text).not.toContain('I detected the general domain');

    const traces = getRoutingTraces();
    expect(traces.some(trace => trace.questionType === 'trace_meta' && trace.traceTarget === 'last_answer')).toBe(true);
    expect(traces.every(trace => Boolean(trace.finalAnswerHandler))).toBe(true);
  });

  it.each(['where did that come from', 'what source was that', 'did that use database', 'did that use AI'])('recognizes generalized trace wording: %s', async message => {
    await handleHermesMessage({ message: 'what paper strategies do we have' });
    const result = await handleHermesMessage({ message });
    expect(result.diagnostics.answerBuilder).toBe('trace_question_handler');
    expect(result.usedModel).toBe(false);
  });
});

describe('dedicated trading and revenue reasoners', () => {
  it.each(['what strategies are available', 'what paper strategies do we have'])('lists concrete Trading Lab context: %s', message => {
    const result = answerTradingQuestion(message);
    expect(result.handler).toBe('trading_strategy_list');
    expect(result.text).toContain('Half Trend Forex Strategy');
  });

  it('refuses a specific trading recommendation without verified evidence', () => {
    const result = answerTradingQuestion('do you have a strategy you recommend');
    expect(result.handler).toBe('trading_evidence_recommendation');
    expect(result.text).toContain('enough verified backtest/report evidence');
  });

  it.each(['how much can we make this month', 'what will make the most money fastest'])('classifies broad revenue wording: %s', message => {
    expect(isRevenueStrategyQuestion(message)).toBe(true);
    expect(answerRevenueStrategy({ usedSupabase: false }).text).toContain('$6,860');
  });
});
