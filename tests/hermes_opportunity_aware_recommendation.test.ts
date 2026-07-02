import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory } from '../src/lib/hermesMemoryStores';
import { resetConversationState, setLastListedItems, setLastSelectedItem } from '../src/lib/hermesConversationState';

const route = (message: string) => routeHermesPriority({ message, selectionMemory: getSelectionMemory() });

describe('opportunity-aware recommendation framework', () => {
  beforeEach(() => resetConversationState());

  it.each(['is it better to fix a toilet or buy a new one', 'is it easier to fix or replace a toilet'])('answers %s with decision and opportunity value', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.routeDecision).toMatchObject({ routeId: 'opportunity_aware_recommendation', domain: 'opportunity_advisor', retrievalPolicy: 'none', actionPolicy: 'none' });
    expect(response.text).toMatch(/Direct answer/);
    expect(response.text).toMatch(/Business opportunity/);
    expect(response.text).toMatch(/Free or low-cost test/);
    expect(response.text).toMatch(/licensing|insurance|permit/);
    expect(response.usedSupabase).toBe(false);
    expect(response.usedModel).toBe(false);
  });

  it('recommends a middleman model before hands-on plumbing', async () => {
    const response = await handleHermesMessage({ message: 'could I be a middleman for toilet sales' });
    expect(response.route).toBe('opportunity_aware_recommendation');
    expect(response.text).toMatch(/lead-gen|referral|affiliate/i);
    expect(response.text).toMatch(/Do not start by becoming the plumber/);
  });
});

describe('physical-world capability boundary', () => {
  beforeEach(() => resetConversationState());

  it('handles car troubleshooting without claiming repair', async () => {
    const response = await handleHermesMessage({ message: 'can you fix my car' });
    expect(response.route).toBe('opportunity_aware_recommendation');
    expect(response.routeDecision.intent).toBe('physical_world_advisory');
    expect(response.text).toMatch(/cannot physically fix/);
    expect(response.text).toMatch(/year, make, model, symptoms/);
    expect(response.text).toMatch(/referral|affiliate|quote comparison/);
  });

  it('handles phone repair with battery and data boundaries', async () => {
    const response = await handleHermesMessage({ message: 'can you repair my phone' });
    expect(response.route).toBe('opportunity_aware_recommendation');
    expect(response.text).toMatch(/cannot physically repair/);
    expect(response.text).toMatch(/Battery safety|data privacy|repair quote comparison/i);
  });

  it('handles sink repair with regulated-trade warnings', async () => {
    const response = await handleHermesMessage({ message: 'can you fix my sink' });
    expect(response.route).toBe('opportunity_aware_recommendation');
    expect(response.text).toMatch(/cannot perform the physical work/);
    expect(response.text).toMatch(/licensing|permitting|qualified professional/);
  });
});

describe('opportunity advisory continuity', () => {
  beforeEach(() => resetConversationState());

  it('provides a free validation follow-up', async () => {
    await handleHermesMessage({ message: 'is it better to fix a toilet or buy a new one' });
    const response = await handleHermesMessage({ message: 'how can I test this for free' });
    expect(response.route).toBe('advisory_followup');
    expect(response.text).toMatch(/free or low-cost validation/);
    expect(response.text).toMatch(/one-page|no-code|5–10/);
  });

  it('carries opportunity risks into follow-up', async () => {
    await handleHermesMessage({ message: 'is it better to fix a toilet or buy a new one' });
    const response = await handleHermesMessage({ message: 'what would stop us' });
    expect(response.route).toBe('advisory_followup');
    expect(response.text).toMatch(/licensing|liability|lead quality|installer dependency/);
  });

  it('answers whether the prior physical problem can become a business', async () => {
    await handleHermesMessage({ message: 'can you fix my sink' });
    const response = await handleHermesMessage({ message: 'can this be a business' });
    expect(response.route).toBe('advisory_followup');
    expect(response.text).toMatch(/can be a business|demand and partner fulfillment/);
  });
});

describe('opportunity route priority protection', () => {
  beforeEach(() => resetConversationState());

  it('keeps Tesla purchase advice in the vehicle advisor', () => expect(route('should I buy the Tesla Model 3')).toMatchObject({ routeId: 'general_advisor', domain: 'vehicle_recommendation' }));
  it('keeps model usage in model status', () => expect(route('what model did you use').routeId).toBe('cost_model_usage_status'));
  it('keeps human experience in casual common', () => expect(route('do you eat').routeId).toBe('casual_common'));
  it('keeps live opportunity inventory in explicit retrieval', () => expect(route('what business opportunities are available').routeId).toBe('explicit_domain_retrieval'));

  it('keeps numbered item selection in selection memory', () => {
    const items = [{ title: 'One', type: 'opportunity' }, { title: 'Two', type: 'opportunity' }, { title: 'Three', type: 'opportunity' }];
    setLastListedItems(items); setLastSelectedItem(items[2]);
    expect(route('number 3').routeId).toBe('memory_followup');
  });

  it('keeps trade execution blocked', () => expect(route('can you place a trade')).toMatchObject({ routeId: 'safety_gate', actionPolicy: 'blocked' }));
  it('keeps CRM implementation approval-gated', () => expect(route('start building the CRM now')).toMatchObject({ routeId: 'approval_action_prepare', actionPolicy: 'approval_required' }));
  it('keeps source questions in trace routing', () => expect(route('where did that answer come from').routeId).toBe('trace_source_meta'));

  it('keeps truly ambiguous help in soft fallback', async () => {
    const response = await handleHermesMessage({ message: 'can you help with it' });
    expect(response.route).toBe('fallback_clarification');
  });
});
