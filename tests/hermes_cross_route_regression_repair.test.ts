import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory } from '../src/lib/hermesMemoryStores';
import { getAdvisoryContinuity } from '../src/lib/hermesAdvisoryContinuity';
import { resetConversationState } from '../src/lib/hermesConversationState';

const route = (message: string) => routeHermesPriority({ message, selectionMemory: getSelectionMemory() });

describe('live-record retrieval priority', () => {
  beforeEach(() => resetConversationState());

  it.each(['what approvals do i have', 'what approvals are pending', 'show my approvals', 'what task requests are pending', 'anything in Ray Review', 'what needs my approval'])('routes %s before advisors and fallback', async message => {
    const decision = route(message);
    expect(decision).toMatchObject({ routeId: 'explicit_domain_retrieval', activationLevel: 2, domain: 'approvals', memoryPolicy: 'none', retrievalPolicy: 'supabase_then_static_fallback', modelPolicy: 'forbidden' });
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('explicit_domain_retrieval');
    expect(response.text).not.toMatch(/do you want a general recommendation|opportunity angle/i);
    expect(response.usedModel).toBe(false);
  });

  it('keeps business opportunities on the protected live-record path', () => {
    expect(route('what business opportunities are available')).toMatchObject({ routeId: 'explicit_domain_retrieval', domain: 'business_opportunity', retrievalPolicy: 'supabase_then_static_fallback' });
  });
});

describe('business selection to advisory continuity', () => {
  beforeEach(() => resetConversationState());

  it('carries a selected implementation plan into feasibility', async () => {
    const inventory = await handleHermesMessage({ message: 'what business opportunities are available' });
    expect(inventory.route).toBe('explicit_domain_retrieval');
    const selected = await handleHermesMessage({ message: 'lets review number 3' });
    expect(selected.route).toBe('memory_followup');
    expect(selected.text).toContain('Monthly Readiness Subscription');
    expect(getAdvisoryContinuity()?.lastAdvisoryTopic).toBe('Monthly Readiness Subscription');
    const feasible = await handleHermesMessage({ message: 'do you think it will work' });
    expect(feasible.route).toBe('advisory_followup');
    expect(feasible.text).toMatch(/Monthly Readiness Subscription can work/);
    expect(feasible.text).not.toMatch(/need one more detail/);
  });

  it('answers risks and first step from the selected plan', async () => {
    await handleHermesMessage({ message: 'what business opportunities are available' });
    await handleHermesMessage({ message: 'lets review number 3' });
    const risks = await handleHermesMessage({ message: 'what would stop us' });
    expect(risks.route).toBe('advisory_followup');
    expect(risks.text).toMatch(/weak retention|unclear deliverables/);
    const start = await handleHermesMessage({ message: 'how do we start' });
    expect(start.route).toBe('advisory_followup');
    expect(start.text).toMatch(/five manual pilot clients/);
  });
});

describe('trading and trace cross-route protection', () => {
  beforeEach(() => resetConversationState());

  it('keeps consecutive trading recommendations honest and local', async () => {
    const first = await handleHermesMessage({ message: 'do you recommend a trading strategy' });
    const second = await handleHermesMessage({ message: 'what is the top trading strategy' });
    expect(first.route).toBe('local_reasoning');
    expect(second.route).toBe('process_settings_reports_status');
    expect(first.text + second.text).toMatch(/paper|demo|backtest|cannot honestly recommend/i);
    expect(first.usedModel || second.usedModel).toBe(false);
  });

  it('answers Supabase capability then explains why trading used local evidence', async () => {
    await handleHermesMessage({ message: 'what is the top trading strategy' });
    const capability = await handleHermesMessage({ message: 'are you connected to supabase' });
    expect(capability.route).toBe('trace_source_meta');
    const reason = await handleHermesMessage({ message: 'so why are you using local' });
    expect(reason.route).toBe('trace_source_meta');
    expect(reason.text).toMatch(/local|Trading|report/i);
    expect(reason.text).not.toMatch(/need one more detail/);
  });
});

describe('fallback and safety boundaries', () => {
  beforeEach(() => resetConversationState());
  it('reserves target clarification for a vague action', async () => {
    const response = await handleHermesMessage({ message: 'Delegate this' });
    expect(response.route).toBe('approval_action_prepare');
    expect(response.text).toMatch(/eligible target|draft-only/);
    expect(response.approvalRequired).toBe(true);
  });
  it('keeps live trade execution blocked', () => expect(route('can you place a trade')).toMatchObject({ routeId: 'safety_gate', actionPolicy: 'blocked' }));
});
