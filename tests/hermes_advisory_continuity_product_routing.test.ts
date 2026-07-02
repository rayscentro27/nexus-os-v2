import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory } from '../src/lib/hermesMemoryStores';
import { getAdvisoryContinuity } from '../src/lib/hermesAdvisoryContinuity';
import { resetConversationState, setLastListedItems, setLastSelectedItem } from '../src/lib/hermesConversationState';

const route = (message: string) => routeHermesPriority({ message, selectionMemory: getSelectionMemory() });

describe('human-experience casual routing', () => {
  beforeEach(() => resetConversationState());

  it.each([
    ['do you eat', /do not eat|do not.*body/],
    ['do you sleep', /do not sleep/],
    ['are you hungry', /do not eat|do not.*body/],
    ['do you have feelings', /do not have feelings/],
  ])('answers %s without operational context', async (message, answer) => {
    const response = await handleHermesMessage({ message });
    expect(response.routeDecision).toMatchObject({ routeId: 'casual_common', intent: 'human_experience_question', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden' });
    expect(response.usedModel).toBe(false);
    expect(response.usedSupabase).toBe(false);
    expect(response.text).toMatch(answer);
    expect(response.text).not.toMatch(/I can help, but I need one more detail/);
  });
});

describe('product model disambiguation', () => {
  beforeEach(() => resetConversationState());

  it.each(['what do you think about the Tesla Model 3', 'what do you thing about the tesla model 3', 'what do you think about the Model Y'])('routes %s as vehicle advice', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.routeDecision).toMatchObject({ routeId: 'general_advisor', domain: 'vehicle_recommendation', intent: 'product_recommendation' });
    expect(response.text).toMatch(/Tesla|charging|insurance|EV/);
    expect(response.routeDecision.domain).not.toBe('model_cost_status');
  });

  it('routes a revenue model to business reasoning, not AI model status', () => {
    const decision = route('what do you think about our revenue model');
    expect(decision.domain).toBe('monetization');
    expect(decision.routeId).not.toBe('cost_model_usage_status');
  });

  it('preserves AI model usage routing', () => {
    expect(route('what model did you use')).toMatchObject({ routeId: 'cost_model_usage_status', domain: 'model_cost_status', modelPolicy: 'forbidden' });
  });
});

describe('advisory continuity', () => {
  beforeEach(() => resetConversationState());

  it('evaluates the prior revenue plan instead of selection memory', async () => {
    await handleHermesMessage({ message: 'what is the fastest way to make money in the next 30 days' });
    const response = await handleHermesMessage({ message: 'do you think it is possible' });
    expect(response.route).toBe('advisory_followup');
    expect(response.text).toMatch(/possible|realistic path|conservative-to-realistic/);
    expect(response.text).not.toMatch(/Name the item|selection policy/);
  });

  it.each(['what would stop us', 'is that realistic'])('answers %s from short-lived plan context', async message => {
    await handleHermesMessage({ message: 'what is the fastest way to make money in the next 30 days' });
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('advisory_followup');
    expect(response.text).toMatch(/blockers|lead flow|realistic|possible/i);
  });

  it('lets trace and explicit product/domain questions override continuity', async () => {
    await handleHermesMessage({ message: 'what is the fastest way to make money in the next 30 days' });
    expect((await handleHermesMessage({ message: 'where did that answer come from' })).route).toBe('trace_source_meta');
    expect((await handleHermesMessage({ message: 'what do you think about the Tesla Model 3' })).route).toBe('general_advisor');
    expect((await handleHermesMessage({ message: 'what business opportunities are available' })).route).toBe('explicit_domain_retrieval');
  });

  it('expires advisory continuity after six intervening turns', async () => {
    await handleHermesMessage({ message: 'what is the fastest way to make money in the next 30 days' });
    for (let index = 0; index < 7; index += 1) await handleHermesMessage({ message: 'Good evening' });
    expect(getAdvisoryContinuity()).toBeNull();
    expect((await handleHermesMessage({ message: 'is that realistic' })).route).toBe('fallback_clarification');
  });
});

describe('Nexus product build planning', () => {
  beforeEach(() => resetConversationState());

  it.each(['can you build me a CRM for Nexus', 'what would it take to build the CRM', 'can you add this feature to Nexus'])('plans %s without claiming execution', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.routeDecision).toMatchObject({ routeId: 'nexus_build_planning', domain: 'nexus_product_build', intent: 'build_planning', actionPolicy: 'none' });
    expect(response.text).toMatch(/CRM|modules|foundation|build plan/i);
    expect(response.text).toMatch(/not created code|have not created code/);
  });

  it('gates an explicit start-building request', async () => {
    const response = await handleHermesMessage({ message: 'start building the CRM now' });
    expect(response.routeDecision).toMatchObject({ routeId: 'approval_action_prepare', activationLevel: 6, actionPolicy: 'approval_required', modelPolicy: 'forbidden' });
    expect(response.text).toMatch(/did not start building|explicit approval/);
  });

  it('keeps the soft fallback for a truly ambiguous target', async () => {
    const response = await handleHermesMessage({ message: 'can you help with it' });
    expect(response.route).toBe('fallback_clarification');
    expect(response.text).toMatch(/need one more detail/);
  });
});

describe('selection and safety regressions', () => {
  beforeEach(() => resetConversationState());
  it('keeps numbered selection ahead of advisory continuity', () => {
    const items = [{ title: 'One', type: 'opportunity' }, { title: 'Two', type: 'opportunity' }, { title: 'Three', type: 'opportunity' }];
    setLastListedItems(items); setLastSelectedItem(items[2]);
    expect(route('number 3')).toMatchObject({ routeId: 'memory_followup', memoryPolicy: 'selection_only' });
  });
  it('still blocks live trade execution', () => expect(route('can you place a trade')).toMatchObject({ routeId: 'safety_gate', actionPolicy: 'blocked' }));
  it('keeps report scheduling approval-gated', () => expect(route('schedule a report next Monday')).toMatchObject({ routeId: 'schedule_action_prepare', actionPolicy: 'approval_required' }));
});
