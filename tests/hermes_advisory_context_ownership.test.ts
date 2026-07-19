import { beforeEach, describe, expect, it } from 'vitest';
import { buildHermesOperatingContext } from '../src/lib/hermes/hermesOperatingContext';
import { runHermesConversation, resetHermesCanonicalConversationSession } from '../src/lib/hermes/hermesConversationEngine';
import type { HermesConversationResult } from '../src/lib/hermes/hermesConversationTypes';

const operatingContext = buildHermesOperatingContext(new Date('2026-07-19T12:00:00.000Z'));

function ask(message: string, session?: HermesConversationResult['session']): HermesConversationResult {
  return runHermesConversation({
    message,
    session,
    actorRole: 'admin',
    channel: 'full_workroom',
    pageContext: { operatingContext },
  });
}

function expectRevenueTopic(result: HermesConversationResult): void {
  expect(result.response).toMatch(/\$97|readiness review|revenue|offer/i);
  expect(result.response).not.toMatch(/Client live-data flag off/i);
}

describe('Hermes advisory context ownership', () => {
  beforeEach(() => resetHermesCanonicalConversationSession());

  it('replaces priority advisory context with the newest revenue recommendation', () => {
    const priority = ask('what should we focus on today?');
    expect(priority.session.activeAdvisoryId).toBe(priority.session.advisoryContext?.advisoryId);
    expect(priority.session.advisoryContext?.topicType).toBe('EXECUTIVE_PRIORITY');
    expect(priority.response).toMatch(/Client live-data flag off/i);

    const firstWhy = ask('why that one?', priority.session);
    expect(firstWhy.response).toMatch(/Client live-data flag off/i);

    const revenue = ask('how can we make money today?', firstWhy.session);
    expect(revenue.session.advisoryContext?.topicType).toBe('REVENUE_ACTION');
    expect(revenue.session.activeAdvisoryId).toBe(revenue.session.advisoryContext?.advisoryId);
    expect(revenue.session.advisoryHistory?.some((item) => item.topicType === 'EXECUTIVE_PRIORITY' && item.status === 'SUPERSEDED')).toBe(true);

    const secondWhy = ask('why that one?', revenue.session);
    expectRevenueTopic(secondWhy);
    expect(secondWhy.trace).toMatchObject({ resolutionMethod: 'ACTIVE_ADVISORY' });
  });

  it('uses the newest revenue context for rationale, feasibility, and blockers', () => {
    let session = ask('what should we focus on today?').session;
    session = ask('how can we make money today?', session).session;

    const rationale = ask('why that one?', session);
    expect(rationale.intent).toBe('followup_rationale');
    expectRevenueTopic(rationale);

    const feasibility = ask('is that realistic?', rationale.session);
    expect(feasibility.intent).toBe('followup_feasibility');
    expectRevenueTopic(feasibility);
    expect(feasibility.response).toMatch(/realistic|test-mode|bounded/i);

    const blockers = ask('what would stop us?', feasibility.session);
    expect(blockers.intent).toBe('followup_blockers');
    expectRevenueTopic(blockers);
    expect(blockers.response).toMatch(/Stripe remains test-only|configuration checks|Lead audience/i);
  });

  it('does not let status or greeting turns steal advisory ownership', () => {
    let session = ask('how can we make money today?').session;
    const stripe = ask('is Stripe live?', session);
    expect(stripe.response).toMatch(/test mode|deferred/i);
    expect(stripe.session.advisoryContext?.topicType).toBe('REVENUE_ACTION');

    const afterStatus = ask('why that one?', stripe.session);
    expectRevenueTopic(afterStatus);

    const thanks = ask('thank you', afterStatus.session);
    expect(thanks.session.advisoryContext?.topicType).toBe('REVENUE_ACTION');

    const afterGreeting = ask('is that realistic?', thanks.session);
    expectRevenueTopic(afterGreeting);
  });

  it('allows explicit older-topic recall without permanently stealing active ownership', () => {
    let session = ask('what should we focus on today?').session;
    session = ask('how can we make money today?', session).session;

    const recalled = ask('going back to the client live-data flag, what would stop us?', session);
    expect(recalled.response).toMatch(/Client live-data flag off|live-data|customer-facing evidence/i);
    expect(recalled.trace).toMatchObject({ resolutionMethod: 'EXPLICIT_TOPIC' });
    expect(recalled.session.advisoryContext?.topicType).toBe('REVENUE_ACTION');

    const activeAgain = ask('why that one?', recalled.session);
    expectRevenueTopic(activeAgain);
  });

  it('lets a risk mitigation response become the newest advisory context', () => {
    let session = ask('how can we make money today?').session;
    const risk = ask('what is our biggest risk right now?', session);
    expect(risk.session.advisoryContext?.topicType).toBe('EXECUTIVE_RISK');

    const why = ask('why that one?', risk.session);
    expect(why.response).toMatch(/Client live-data flag off|customer-facing evidence|risk/i);
    expect(why.response).not.toMatch(/\$97 readiness review/i);
  });

  it('targets the currently selected revenue recommendation for explicit governed task requests', () => {
    let session = ask('give me three ways to make money today').session;
    const second = ask('go deeper on number 2', session);
    expect(second.referencesResolved).toContain('number 2');
    expect(second.response).toMatch(/lead|reactivation|offer|money action/i);

    const task = ask('turn that one into a task', second.session);
    expect(task.mode).toBe('TASK_REQUEST');
    expect(task.action).toMatchObject({ type: 'CREATE_GOVERNED_TASK', requiresApproval: true });
    expect(JSON.stringify(task.action)).not.toMatch(/function|onClick|callback/i);
  });
});
