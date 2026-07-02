import { beforeEach, describe, expect, it } from 'vitest';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { createRouteDecision, assertRouteDecisionIntegrity } from '../src/lib/hermesRouteDecision';
import { buildContextPacket } from '../src/lib/hermesContextPacketBuilder';
import { containsDiagnosticLeak, renderHermesAnswer } from '../src/lib/hermesAnswerRenderer';
import { getConversationState, resetConversationState, setLastListedItems, setLastSelectedItem } from '../src/lib/hermesConversationState';
import { getSelectionMemory } from '../src/lib/hermesMemoryStores';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';

const items = [
  { title: '$97 Credit & Funding Readiness Review', type: 'opportunity' },
  { title: '$297 Credit Assistant Plan', type: 'opportunity' },
  { title: 'Monthly Readiness Subscription', type: 'opportunity' },
];

const route = (message: string, previousDomain: string | null = 'business_opportunity') => routeHermesPriority({ message, previousDomain, selectionMemory: getSelectionMemory() });

describe('RouteDecision policy contract', () => {
  beforeEach(() => { resetConversationState(); setLastListedItems(items); setLastSelectedItem(items[2]); });

  it('isolates source questions to last trace only', () => {
    const decision = route('Where did you get your last response from?');
    expect(decision).toMatchObject({ routeId: 'trace_source_meta', memoryPolicy: 'last_trace_only', retrievalPolicy: 'none', modelPolicy: 'forbidden' });
    expect(decision.allowedContext.selectionMemory).toBe(false);
  });

  it('routes Supabase status without model or business memory', () => {
    const decision = route('Are you using Supabase?');
    expect(decision.routeId).toBe('trace_source_meta');
    expect(decision.allowedContext.model).toBe(false);
    expect(decision.allowedContext.selectionMemory).toBe(false);
  });

  it('answers model-use questions from trace with model forbidden', () => {
    const decision = route('What model did you use?');
    expect(decision.routeId).toBe('cost_model_usage_status');
    expect(decision.modelPolicy).toBe('forbidden');
  });

  it('requires retrieve-first local reports for Trading Lab inventory', () => {
    const decision = route('What strategies are in the Trading Lab?', 'trading');
    expect(decision).toMatchObject({ routeId: 'explicit_domain_retrieval', activationLevel: 2, domain: 'trading', memoryPolicy: 'none', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden' });
  });

  it('uses long-term context but not selection for revenue reasoning', () => {
    const decision = route('What is the most money we can make over the next 30 days?');
    expect(decision).toMatchObject({ routeId: 'revenue_reasoning', domain: 'monetization', memoryPolicy: 'long_term_allowed', diagnosticsPolicy: 'hidden' });
    expect(decision.allowedContext.selectionMemory).toBe(false);
  });

  it('permits selection memory for numbered implementation follow-ups', () => {
    const decision = route('Number 3 how do we implement?');
    expect(decision).toMatchObject({ routeId: 'memory_followup', memoryPolicy: 'selection_only' });
    const packet = buildContextPacket({ routeDecision: decision, message: 'Number 3 how do we implement?', conversationState: getConversationState() });
    expect(packet.selectionMemory).not.toBeNull();
  });

  it('treats "that" in source wording as trace, not selection memory', () => {
    const decision = route('Where did that come from?');
    expect(decision.routeId).toBe('trace_source_meta');
    expect(decision.allowedContext.selectionMemory).toBe(false);
  });

  it('allows selection only for an approval draft and performs no execution', async () => {
    const decision = route('Create a Ray Review card for that.');
    expect(decision).toMatchObject({ routeId: 'approval_action_prepare', actionPolicy: 'approval_required', memoryPolicy: 'selection_only', modelPolicy: 'forbidden' });
    const response = await handleHermesMessage({ message: 'Create a Ray Review card for that.' });
    expect(response.approvalRequired).toBe(true);
    expect(response.text).toContain('not been saved or submitted');
  });

  it('hard-blocks trade execution before all context', () => {
    const decision = route('Can you place a trade?');
    expect(decision).toMatchObject({ routeId: 'safety_gate', actionPolicy: 'blocked', modelPolicy: 'forbidden', memoryPolicy: 'none', retrievalPolicy: 'none' });
  });

  it('suppresses diagnostic leaks in hidden answer mode', () => {
    const decision = route('What is the most money we can make over the next 30 days?');
    const rendered = renderHermesAnswer({ userAnswer: 'I detected the general domain. Domain override applied.', internalTrace: 'debug', selectedEntities: [], sources: [], nextActions: [], safeFallbackAnswer: 'Plain revenue answer.' }, decision);
    expect(rendered).toEqual({ text: 'Plain revenue answer.', diagnosticSuppressed: true });
    expect(containsDiagnosticLeak(rendered.text)).toBe(false);
  });

  it('rejects internally inconsistent contracts', () => {
    expect(() => createRouteDecision({ routeId: 'bad', activationLevel: 1, domain: 'x', intent: 'x', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden', diagnosticsPolicy: 'hidden', actionPolicy: 'none', reason: 'test', allowedContext: { model: true } })).toThrow();
    expect(assertRouteDecisionIntegrity(route('Can you place a trade?'))).toBe(true);
  });
});

describe('policy-compliant user answers', () => {
  beforeEach(() => resetConversationState());
  it.each([
    'What strategies are in the Trading Lab?',
    'What is the most money we can make over the next 30 days?',
    'Who are you?',
  ])('does not leak diagnostics for %s', async message => {
    const response = await handleHermesMessage({ message });
    expect(containsDiagnosticLeak(response.text)).toBe(false);
    expect(response.routeDecision.diagnosticsPolicy).toBe('hidden');
  });
});
