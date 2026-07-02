import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { resetConversationState } from '../src/lib/hermesConversationState';
import { setHermesMemoryScope } from '../src/lib/hermesMemoryStores';
import { clearSession, getActiveSession } from '../src/lib/hermesAdvisorSession';
import { buildIntentFrame } from '../src/lib/hermesIntentClassifier';
import { classifyConversationMove } from '../src/lib/hermesConversationMoveClassifier';
import { cleanRecordSourceSummary, renderRecordContract } from '../src/lib/hermesOperationalContracts';
import { getHermesDecisionState } from '../src/lib/hermesDecisionState';

const scope = { tenantId: 'state-arbiter-test', sessionId: 'default' };
const scopeKey = 'state-arbiter-test:default';

describe('Hermes state arbiter consolidation', () => {
  beforeEach(() => { setHermesMemoryScope(scopeKey); resetConversationState(); clearSession(scopeKey); });

  it('classifies safety, recommendation, navigation, depth, and timeline moves', () => {
    const state = getHermesDecisionState(scopeKey);
    state.lastSafetyDecision = { request: 'send email', reason: 'external action', blockedAction: 'email', safeAlternatives: ['draft'], timestamp: new Date().toISOString() };
    state.lastRecommendation = { label: '$97 Review', domain: 'business_opportunities', reason: 'low barrier', source: 'static', timestamp: new Date().toISOString() };
    expect(classifyConversationMove({ message: 'why did you block that', intentFrame: buildIntentFrame('why did you block that'), activeSession: null, decisionState: state }).conversationMove).toBe('safety_explanation_followup');
    expect(classifyConversationMove({ message: 'why do you recommend that one', intentFrame: buildIntentFrame('why do you recommend that one'), activeSession: null, decisionState: state }).conversationMove).toBe('last_recommendation_followup');
    expect(classifyConversationMove({ message: 'give me the audit version', intentFrame: buildIntentFrame('give me the audit version'), activeSession: null, decisionState: state }).conversationMove).toBe('response_depth_change');
    expect(classifyConversationMove({ message: 'what did we work on yesterday', intentFrame: buildIntentFrame('what did we work on yesterday'), activeSession: null, decisionState: state }).conversationMove).toBe('timeline_recap');
  });

  it('stores and explains the last safety decision', async () => {
    const blocked = await handleHermesMessage({ message: 'send an email to all clients about the $97 Credit & Funding Readiness Review', ...scope });
    expect(blocked.route).toBe('safety_gate');
    expect(blocked.text).toMatch(/cannot execute|blocked|approval/i);
    const why = await handleHermesMessage({ message: 'why did you block that', ...scope });
    expect(why.route).toBe('safety_explanation');
    expect(why.text).toMatch(/external action|requires approval|draft the email/i);
    expect(why.route).not.toBe('fallback_clarification');
  });

  it('keeps approvals provenance global and out of sessions', async () => {
    await handleHermesMessage({ message: 'do I have approvals pending', ...scope });
    const provenance = await handleHermesMessage({ message: 'where did you get that answer from', ...scope });
    expect(provenance.route).toBe('trace_source_meta');
    expect(provenance.text).toMatch(/approval|task_requests|supabase|source/i);
  });

  it('classifies a successful zero-row client read as empty_success', () => {
    const live = { text: '', source: 'live_supabase_context', sourceType: 'live_supabase' as const, liveData: true, timestamp: '2026-07-02T00:00:00Z', tablesQueried: ['client_profiles'], rowCounts: { client_profiles: 0 }, tableResults: { client_profiles: { status: 'success' as const, rowCount: 0 } }, verificationStatus: 'verified' as const };
    expect(cleanRecordSourceSummary('clients', live)).toMatchObject({ status: 'empty_success', source: 'client_profiles', rowCount: 0 });
    const text = renderRecordContract('clients', live);
    expect(text).toMatch(/0 client rows|empty_success|client_profiles/i);
    expect(text).not.toMatch(/read failed|not verified|Source checked:[^\n]*task_requests/i);
  });

  it('prevents stale report session from hijacking recommendation rationale', async () => {
    await handleHermesMessage({ message: 'what reports are available', ...scope });
    await handleHermesMessage({ message: 'can we review them', ...scope });
    await handleHermesMessage({ message: 'next', ...scope });
    await handleHermesMessage({ message: 'what is the top business opportunity', ...scope });
    const why = await handleHermesMessage({ message: 'why do you recommend that one', ...scope });
    expect(why.route).toBe('recommendation_explanation');
    expect(why.text).toMatch(/\$97|lowest launch barrier|entry offer/i);
    expect(why.text).not.toMatch(/Final Daily Activation Master/i);
  });

  it('advances the report cursor on consecutive next commands', async () => {
    await handleHermesMessage({ message: 'what reports are available', ...scope });
    await handleHermesMessage({ message: 'can we review them', ...scope });
    const firstFocus = getActiveSession(scopeKey)?.currentFocus?.label;
    const second = await handleHermesMessage({ message: 'next', ...scope });
    const secondFocus = getActiveSession(scopeKey)?.currentFocus?.label;
    const third = await handleHermesMessage({ message: 'next', ...scope });
    const thirdFocus = getActiveSession(scopeKey)?.currentFocus?.label;
    expect(second.route).toBe('active_session_continue');
    expect(third.route).toBe('active_session_continue');
    expect(secondFocus).not.toBe(firstFocus);
    expect(thirdFocus).not.toBe(secondFocus);
  });

  it('continues business blockers and resolves a conversation-only Ray Review draft', async () => {
    await handleHermesMessage({ message: 'pull up the business opportunity report and lets review each new opportunity and why each score was given', ...scope });
    await handleHermesMessage({ message: 'start with the highest scored one', ...scope });
    const blockers = await handleHermesMessage({ message: 'what would stop us', ...scope });
    expect(blockers.route).toBe('active_session_continue');
    expect(blockers.text).toMatch(/lead flow|offer scope|fulfillment|proof|checkout|compliance/i);
    const draft = await handleHermesMessage({ message: 'create a Ray Review draft for that', ...scope });
    expect(draft.text).toMatch(/Ray Review Draft|\$97 Credit & Funding Readiness Review/i);
    expect(draft.text).toMatch(/not saved.*not submitted.*not executed/is);
  });

  it('rerenders system health in CEO and audit modes without fallback', async () => {
    await handleHermesMessage({ message: 'what is the system health', ...scope });
    const ceo = await handleHermesMessage({ message: 'give me the CEO version', ...scope });
    expect(ceo.route).toBe('response_mode_change');
    expect(ceo.text.length).toBeLessThan(1000);
    expect(ceo.text).not.toMatch(/reports\//i);
    const audit = await handleHermesMessage({ message: 'give me the audit version', ...scope });
    expect(audit.route).toBe('response_mode_change');
    expect(audit.text).toMatch(/Audit details|Sources:|Timestamp:|Confidence:/i);
  });

  it('routes yesterday to a verified-or-explicitly-missing timeline recap', async () => {
    const recap = await handleHermesMessage({ message: 'what did we work on yesterday', ...scope });
    expect(recap.route).toBe('process_activity_status');
    expect(recap.text).toMatch(/yesterday|do not have verified activity|activity/i);
    expect(recap.route).not.toBe('fallback_clarification');
  });

  it('keeps default rendered answers free of raw paths, UUID dumps, and route debug blocks', async () => {
    const answer = await handleHermesMessage({ message: 'what is the system health', ...scope });
    expect(answer.text).not.toMatch(/reports\/[\w./-]+/i);
    expect(answer.text).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i);
    expect(answer.text).not.toMatch(/Full routing trace|Allowed context:/i);
  });
});
