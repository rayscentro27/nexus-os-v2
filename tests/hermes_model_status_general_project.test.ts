import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { answerHermesTraceQuestion } from '../src/lib/hermesTraceQuestionHandler';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory } from '../src/lib/hermesMemoryStores';
import { resetConversationState } from '../src/lib/hermesConversationState';

const route = (message: string) => routeHermesPriority({ message, selectionMemory: getSelectionMemory() });

describe('model status without trace', () => {
  beforeEach(() => resetConversationState());

  it('uses capability status when no prior routing record exists', () => {
    const decision = route('what model did you use');
    const answer = answerHermesTraceQuestion('what model did you use', null, { routeDecision: decision });
    expect(answer).toMatch(/do not have a previous routing record/);
    expect(answer).toMatch(/configured|does not currently prove/);
    expect(answer).not.toBe('No prior routing record is available.');
    expect(answer).not.toMatch(/last answer used the model/i);
  });

  it('answers from the trace when a prior answer exists', async () => {
    await handleHermesMessage({ message: 'what color is the sky' });
    const response = await handleHermesMessage({ message: 'what model did you use' });
    expect(response.route).toBe('cost_model_usage_status');
    expect(response.text).toMatch(/No\. The last answer|no model call was made/);
  });

  it('routes current-model wording to deterministic model status', () => {
    expect(route('what model are you using')).toMatchObject({ routeId: 'cost_model_usage_status', modelPolicy: 'forbidden' });
  });
});

describe('general project planning and typo normalization', () => {
  beforeEach(() => resetConversationState());

  it.each(['can you build me a house', 'can tyou build me a house', 'what would it take to build a house'])('plans %s without claiming physical work', async message => {
    const response = await handleHermesMessage({ message });
    expect(response.routeDecision).toMatchObject({ routeId: 'general_project_planning', domain: 'general_project', intent: 'project_planning_or_feasibility', actionPolicy: 'none' });
    expect(response.text).toMatch(/cannot physically build|help you plan/);
    expect(response.text).not.toMatch(/built your house|filed.*permit|hired.*contractor/i);
  });

  it('plans an app without claiming code or files', async () => {
    const response = await handleHermesMessage({ message: 'can you help me build an app' });
    expect(response.route).toBe('general_project_planning');
    expect(response.text).toMatch(/plan an app/);
    expect(response.text).toMatch(/not created code or files/);
  });

  it('normalizes common advisor typos before routing', () => {
    expect(route('what is the fatest way to make money in 30 days').routeId).toBe('revenue_reasoning');
    expect(route('what laptop do you recomend').routeId).not.toBe('fallback_clarification');
  });
});

describe('fallback clarification continuity', () => {
  beforeEach(() => resetConversationState());

  it('resumes an ambiguous question as a general recommendation', async () => {
    const first = await handleHermesMessage({ message: 'can you help with it' });
    expect(first.route).toBe('fallback_clarification');
    expect(first.text).toMatch(/general recommendation/);
    const resumed = await handleHermesMessage({ message: 'general recommendation' });
    expect(resumed.route).toBe('fallback_continuation');
    expect(resumed.text).toMatch(/Under a general recommendation/);
    expect(resumed.text).not.toMatch(/do you want a general recommendation/);
  });

  it('resumes an ambiguous question under Nexus planning', async () => {
    await handleHermesMessage({ message: 'can you help with it' });
    const resumed = await handleHermesMessage({ message: 'Nexus' });
    expect(resumed.route).toBe('fallback_continuation');
    expect(resumed.routeDecision.domain).toBe('nexus_product_build');
    expect(resumed.text).toMatch(/Under Nexus planning/);
    expect(resumed.text).toMatch(/not created code/);
  });
});

describe('priority regressions', () => {
  beforeEach(() => resetConversationState());
  it('keeps Tesla product wording out of model status', () => expect(route('what do you think about the Tesla Model 3')).toMatchObject({ routeId: 'general_advisor', domain: 'vehicle_recommendation' }));
  it('keeps Nexus CRM planning distinct', () => expect(route('can you build me a CRM for Nexus').routeId).toBe('nexus_build_planning'));
  it('gates explicit implementation', () => expect(route('start building the CRM now')).toMatchObject({ routeId: 'approval_action_prepare', actionPolicy: 'approval_required' }));
  it('blocks live trade execution', () => expect(route('can you place a trade')).toMatchObject({ routeId: 'safety_gate', actionPolicy: 'blocked' }));
});
