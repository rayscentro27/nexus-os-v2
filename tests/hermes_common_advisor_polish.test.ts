import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory } from '../src/lib/hermesMemoryStores';
import { resetConversationState, setLastListedItems, setLastSelectedItem } from '../src/lib/hermesConversationState';

const items = [
  { title: '$97 Credit & Funding Readiness Review', type: 'opportunity' },
  { title: '$297 Credit Assistant Plan', type: 'opportunity' },
  { title: 'Monthly Readiness Subscription', type: 'opportunity' },
];
const route = (message: string) => routeHermesPriority({ message, previousDomain: 'business_opportunity', selectionMemory: getSelectionMemory() });

describe('Hermes common conversation and advisor layer', () => {
  beforeEach(() => { resetConversationState(); setLastListedItems(items); setLastSelectedItem(items[2]); });

  it.each(['What is your favorite ice cream?', 'How did you sleep?', 'What color is the sky?', 'What do you think about pizza?'])('routes %s without stale memory or retrieval', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('casual_common');
    expect(response.routeDecision).toMatchObject({ memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden' });
    expect(response.text).not.toMatch(/not enough current page|Readiness Review/);
    expect(response.usedSupabase).toBe(false);
    expect(response.usedModel).toBe(false);
  });

  it.each(['What car would you recommend for me?', 'What laptop should I buy?'])('provides general advice for %s', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('general_advisor');
    expect(response.routeDecision.allowedContext.selectionMemory).toBe(false);
    expect(response.text).not.toMatch(/not enough current page|Readiness Review/);
  });

  it('keeps an explicit prior-list recommendation as a memory follow-up', () => {
    expect(route('Which one do you recommend for me?').routeId).toBe('memory_followup');
  });

  it('does not treat a domain-specific favorite as casual', () => {
    expect(route('What is your favorite business opportunity?').routeId).not.toBe('casual_common');
  });
});

describe('Hermes scheduling and action proof', () => {
  beforeEach(() => resetConversationState());

  it('distinguishes report inventory from scheduling', () => {
    expect(route('What reports do we have?').actionPolicy).toBe('none');
    expect(route('Can you schedule a report for next week?')).toMatchObject({ routeId: 'schedule_action_prepare', activationLevel: 6, actionPolicy: 'approval_required', modelPolicy: 'forbidden' });
    expect(route('Send me a report every Monday')).toMatchObject({ routeId: 'schedule_action_prepare', actionPolicy: 'approval_required' });
  });

  it('prepares only a local scheduling draft and starts no scheduler', async () => {
    const response = await handleHermesMessage({ message: 'Schedule the weekly monetization report for next Monday at 9 AM.' });
    expect(response.text).toMatch(/conversation only|not been saved/);
    expect(response.text).toContain('No scheduler was started');
    expect(response.approvalRequired).toBe(true);
  });

  it('asks for missing schedule details', async () => {
    const response = await handleHermesMessage({ message: 'Can you schedule a report for next week?' });
    expect(response.route).toBe('schedule_action_prepare');
    expect(response.text).toMatch(/Which report.*day\/time/);
  });

  it('blocks scheduler activation', async () => {
    const response = await handleHermesMessage({ message: 'Start the report scheduler' });
    expect(response.routeDecision.actionPolicy).toBe('blocked');
  });

  it('uses precise local-only Ray Review language', async () => {
    setLastListedItems(items); setLastSelectedItem(items[2]);
    const response = await handleHermesMessage({ message: 'Create a Ray Review card for that' });
    expect(response.text).toMatch(/conversation only|not been saved/);
    expect(response.text).not.toMatch(/card created/i);
  });

  it('answers action proof from the prior trace', async () => {
    setLastListedItems(items); setLastSelectedItem(items[2]);
    await handleHermesMessage({ message: 'Create a Ray Review card for that' });
    const response = await handleHermesMessage({ message: 'Did that create an actual saved record or only a draft?' });
    expect(response.route).toBe('trace_source_meta');
    expect(response.text).toMatch(/draft prepared in this conversation only|not saved/);
  });
});

describe('human trace wording', () => {
  beforeEach(() => resetConversationState());
  it('returns plain source wording by default and full details only on request', async () => {
    await handleHermesMessage({ message: 'What color is the sky?' });
    const plain = await handleHermesMessage({ message: 'Where did that come from?' });
    expect(plain.text).toMatch(/answer came from/);
    expect(plain.text).not.toMatch(/Memory policy:|Retrieval policy:/);
    const full = await handleHermesMessage({ message: 'Show full trace for that.' });
    expect(full.text).toMatch(/Full routing trace|Memory policy:/);
  });
});
