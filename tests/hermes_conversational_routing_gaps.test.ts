import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory } from '../src/lib/hermesMemoryStores';
import { getConversationState, resetConversationState, setLastListedItems, setLastSelectedItem } from '../src/lib/hermesConversationState';

const items = [
  { title: '$97 Credit & Funding Readiness Review', type: 'opportunity' },
  { title: '$297 Credit Assistant Plan', type: 'opportunity' },
  { title: 'Monthly Readiness Subscription', type: 'opportunity' },
];
const route = (message: string) => routeHermesPriority({ message, previousDomain: getConversationState().lastTopic, selectionMemory: getSelectionMemory() });
const noHarshFallback = (text: string) => expect(text).not.toMatch(/not enough current page|eligible selection context|Name the target/);

describe('greeting and work-opener coverage', () => {
  beforeEach(() => resetConversationState());

  it.each(['Good evening', 'Hey Hermes', 'Are you there?', 'Ready to work?', "Let's get started"])('routes %s as a no-model check-in', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('casual_common');
    expect(response.routeDecision).toMatchObject({ activationLevel: 1, intent: 'greeting_or_light_check_in', memoryPolicy: 'none', retrievalPolicy: 'none', modelPolicy: 'forbidden' });
    expect(response.usedSupabase).toBe(false);
    expect(response.usedModel).toBe(false);
    noHarshFallback(response.text);
  });

  it.each(['Where did we leave off?', "What's next?"])('routes %s to local activity status', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('process_activity_status');
    expect(response.routeDecision).toMatchObject({ domain: 'activity_summary', retrievalPolicy: 'local_reports', modelPolicy: 'forbidden' });
    noHarshFallback(response.text);
  });

  it('lets activity, trace, and safety override greeting language', () => {
    expect(route('Good evening, what did we complete today?').routeId).toBe('process_activity_status');
    expect(route('Good morning, are you connected to Supabase?').routeId).toBe('trace_source_meta');
    expect(route('Hey, can you place a trade?').routeId).toBe('safety_gate');
  });
});

describe('completed-work and trace follow-up coverage', () => {
  beforeEach(() => resetConversationState());

  it.each(['what do we complete today', 'what did we complete today', 'what did OpenCode finish'])('answers %s from local status evidence', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('process_activity_status');
    expect(response.usedModel).toBe(false);
    expect(response.text).toMatch(/last confirmed|completed|activity|commit 556c95a/i);
    noHarshFallback(response.text);
  });

  it.each(["why didn’t you use Supabase", 'why did you use local fallback', 'so why are you using local'])('classifies %s as a source reason follow-up', message => {
    const decision = route(message);
    expect(decision).toMatchObject({ routeId: 'trace_source_meta', intent: 'source_reason_followup', memoryPolicy: 'last_trace_only', retrievalPolicy: 'none', modelPolicy: 'forbidden' });
  });

  it('explains local use from the last non-trace answer', async () => {
    await handleHermesMessage({ message: 'what did we complete today' });
    await handleHermesMessage({ message: 'are you connected to Supabase' });
    const response = await handleHermesMessage({ message: 'so why are you using local' });
    expect(response.route).toBe('trace_source_meta');
    expect(response.text).toMatch(/used local|local activity|local nexus/i);
    expect(response.usedSupabase).toBe(false);
    expect(response.usedModel).toBe(false);
    noHarshFallback(response.text);
  });
});

describe('fallback scope and topic preservation', () => {
  beforeEach(() => resetConversationState());

  it('reserves target clarification for unresolved vague actions', async () => {
    const response = await handleHermesMessage({ message: 'Delegate this' });
    expect(response.route).toBe('approval_action_prepare');
    expect(response.routeDecision.intent).toBe('unresolved_action_reference');
    expect(response.text).toMatch(/eligible target|draft-only/);
    expect(response.approvalRequired).toBe(true);
  });

  it('uses record-specific missing context for an unverified client record', async () => {
    const response = await handleHermesMessage({ message: "what is the client John's last uploaded document" });
    expect(response.text).toMatch(/verified Nexus data|client, report, table, or item/);
  });

  it.each(['what color is the sky', 'what car would you recommend for me'])('does not use fallback for %s', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.route).not.toBe('fallback_clarification');
    noHarshFallback(response.text);
  });

  it('keeps selection and topic intact across greeting, status, and trace turns', async () => {
    setLastListedItems(items); setLastSelectedItem(items[2]);
    const topicBefore = getConversationState().lastTopic;
    await handleHermesMessage({ message: 'Good evening' });
    await handleHermesMessage({ message: 'what did we complete today' });
    await handleHermesMessage({ message: 'why did you use local' });
    expect(getSelectionMemory().lastSelectedItem?.title).toBe('Monthly Readiness Subscription');
    expect(getConversationState().lastTopic).toBe(topicBefore);
  });
});
