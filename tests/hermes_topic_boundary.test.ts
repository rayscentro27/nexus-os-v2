import { beforeEach, describe, expect, it } from 'vitest';
import { classifyHermesDomain } from '../src/lib/hermesDomainClassifier';
import { evaluateTopicBoundary } from '../src/lib/hermesTopicBoundary';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import {
  resetConversationState, setLastListedItems, setLastRankedList,
  setLastRecommendedItem, setLastSelectedItem,
} from '../src/lib/hermesConversationState';
import { reasonAboutMessage } from '../src/lib/hermesReasoningEngine';
import { auditHermesRoutingDecision } from '../src/lib/hermesRoutingDecisionAudit';

const items = [
  { title: '$97 Credit & Funding Readiness Review', type: 'opportunity' },
  { title: '$297 Credit Assistant Plan', type: 'opportunity' },
  { title: 'Monthly Readiness Subscription', type: 'opportunity' },
  { title: 'Funding Application Prep Sprint', type: 'opportunity' },
];

function seedBusinessMemory() {
  setLastListedItems(items);
  setLastRankedList(items);
  setLastRecommendedItem(items[0]);
  setLastSelectedItem(items[2]);
}

describe('Hermes semantic domain classification', () => {
  it.each([
    ['what kind of car would you choose', 'casual_identity'],
    ['who are you', 'casual_identity'],
    ['what forex setup should we test', 'trading'],
    ['should we run a paper trade', 'trading'],
    ['is channel research writing results', 'research_youtube'],
    ['which configuration is missing', 'settings'],
    ['what reports changed', 'reports'],
    ['did you use Supabase', 'model_cost_status'],
    ['what can make money fastest', 'monetization'],
  ])('classifies %s without an exact command route', (message, expected) => {
    expect(classifyHermesDomain(message).domain).toBe(expected);
  });
});

describe('topic boundary eligibility', () => {
  it('rejects stale business memory for casual and explicit domains', () => {
    for (const message of ['favorite food', 'what forex setup should we test', 'what reports changed']) {
      const domain = classifyHermesDomain(message).domain;
      const boundary = evaluateTopicBoundary({ message, detectedDomain: domain, previousTopic: 'business_opportunity', previousSelectedItem: items[0], previousRankedItems: items });
      expect(boundary.shouldUsePriorMemory).toBe(false);
      expect(boundary.reason).toBeTruthy();
    }
  });

  it.each(['number 3', 'the third one', 'that one', 'how do we implement it', 'the monthly readiness subscription'])('accepts valid continuation: %s', message => {
    const boundary = evaluateTopicBoundary({ message, detectedDomain: classifyHermesDomain(message).domain, previousTopic: 'business_opportunity', previousSelectedItem: items[0], previousRankedItems: items });
    expect(boundary.shouldUsePriorMemory).toBe(true);
  });

  it('creates a fresh context for a broad strategy question', () => {
    const message = 'what is the easiest low cost offer to launch';
    const boundary = evaluateTopicBoundary({ message, detectedDomain: classifyHermesDomain(message).domain, previousTopic: 'trading', previousSelectedItem: { title: 'Paper Strategy', type: 'strategy' } });
    expect(boundary.shouldUsePriorMemory).toBe(false);
    expect(boundary.isNewTopic).toBe(true);
  });
});

describe('routing decision audit', () => {
  it('diagnoses the historical Level 4 overmatch without phrase-specific logic', () => {
    const audit = auditHermesRoutingDecision({
      message: 'what kind of vehicle would you choose',
      previousConversationState: { lastTopic: 'business_opportunity', lastSelectedItem: items[0], lastRankedList: items },
      actualResult: { activationLevel: 4, route: 'local_reasoning', sourceMode: 'reasoning', usedSupabase: false, usedModel: false },
    });
    expect(audit.shouldUseMemory).toBe(false);
    expect(audit.actualActivationLevel).toBe(4);
    expect(audit.expectedActivationLevel).toBe(1);
    expect(audit.patchTarget).toContain('activation');
  });

  it('reports a correct post-fix domain override', async () => {
    resetConversationState(); seedBusinessMemory();
    const before = { ...((await import('../src/lib/hermesConversationState')).getConversationState()) };
    const result = await handleHermesMessage({ message: 'which forex setup should we test' });
    const audit = auditHermesRoutingDecision({ message: 'which forex setup should we test', previousConversationState: before, actualResult: result });
    expect(audit.detectedDomain).toBe('trading');
    expect(audit.shouldUseMemory).toBe(false);
    expect(audit.actualActivationLevel).toBe(audit.expectedActivationLevel);
  });
});

describe('pipeline memory boundary', () => {
  beforeEach(() => resetConversationState());

  it.each(['what is your favorite car', 'what kind of car would you choose', 'who are you', 'what should I call you', 'how are you today', 'favorite food'])('does not leak a business recommendation into casual input: %s', async message => {
    seedBusinessMemory();
    const result = await handleHermesMessage({ message });
    expect(result.activationLevel).toBe(1);
    expect(result.usedModel).toBe(false);
    expect(result.usedSupabase).toBe(false);
    expect(result.text).not.toContain('$97 Credit');
    expect(result.diagnostics.memoryUsed).toBe(false);
    expect(result.diagnostics.memoryRejected).toBe(true);
  });

  it.each(['what trading strategy do you recommend', 'what forex setup should we test', 'should we run a paper trade', 'what did the trading lab last prove'])('routes trading semantically and rejects business memory: %s', async message => {
    seedBusinessMemory();
    const result = await handleHermesMessage({ message });
    expect(result.text.toLowerCase()).toMatch(/trading|paper|broker|backtest/);
    expect(result.text).not.toContain('$97 Credit');
    expect(result.diagnostics.memoryUsed).toBe(false);
    expect(result.usedModel).toBe(false);
  });

  it.each([
    ['number 3', 'Monthly Readiness Subscription'],
    ['the third one', 'Monthly Readiness Subscription'],
    ['that one', 'Monthly Readiness Subscription'],
    ['the monthly readiness subscription', 'Monthly Readiness Subscription'],
    ['how do we implement it', 'Monthly Readiness Subscription'],
  ])('uses eligible memory for %s', async (message, expected) => {
    seedBusinessMemory();
    const result = await handleHermesMessage({ message });
    expect(result.text).toContain(expected);
    expect(result.diagnostics.memoryUsed).toBe(true);
  });

  it('uses eligible memory in an approval draft without executing it', async () => {
    seedBusinessMemory();
    const result = await handleHermesMessage({ message: 'create a Ray Review card for that' });
    expect(result.activationLevel).toBe(6);
    expect(result.approvalRequired).toBe(true);
    expect(result.text).toContain('not submitted or executed');
    expect(result.text).toContain('Monthly Readiness Subscription');
  });

  it.each(['what business should I start in 30 days', 'what is the easiest low cost offer to launch', 'what can make money fastest', 'what should we monetize first'])('creates a fresh business recommendation context: %s', async message => {
    seedBusinessMemory();
    const result = await handleHermesMessage({ message });
    expect(result.text).toContain('$97 Credit & Funding Readiness Review');
    expect(result.diagnostics.memoryUsed).toBe(false);
    expect(result.activationLevel).toBe(4);
  });

  it.each(['did you use the model', 'did you use Supabase', 'why did you answer that way', 'what route did that take'])('keeps route diagnostics local: %s', async message => {
    seedBusinessMemory();
    const result = await handleHermesMessage({ message });
    expect(result.activationLevel).toBe(1);
    expect(result.usedModel).toBe(false);
    expect(result.usedSupabase).toBe(false);
  });

  it('passes a rejected boundary into the reasoning engine', () => {
    seedBusinessMemory();
    const plan = reasonAboutMessage('number 3', null, 'page_context', 'no_model', { shouldUsePriorMemory: false, reason: 'topic changed' });
    expect(plan.memoryRejected).toBe(true);
    expect(plan.selectedMemoryItem).toBeNull();
  });
});
