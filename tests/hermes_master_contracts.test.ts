import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { resetConversationState } from '../src/lib/hermesConversationState';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory, setHermesMemoryScope } from '../src/lib/hermesMemoryStores';
import { renderRecordContract } from '../src/lib/hermesOperationalContracts';
import { hermesStore } from '../src/lib/hermesChatStore';

const bannedStatus = /I can reason from the allowed|I need a concrete decision|general recommendation, a Nexus build plan/i;
const route = (message: string) => routeHermesPriority({ message, selectionMemory: getSelectionMemory() });

describe('Hermes master route and renderer contracts', () => {
  beforeEach(() => { setHermesMemoryScope('default:default'); resetConversationState(); });

  it.each([
    ['good morning'], ['how are you today'], ['do you eat'], ['what is your favorite ice cream'],
  ])('keeps casual prompt "%s" isolated from Nexus sources and memory', async (message) => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe('casual_common');
    expect(response.usedSupabase).toBe(false);
    expect(response.usedModel).toBe(false);
    expect(response.rememberedContext).toBe(false);
    expect(response.text).not.toMatch(/allowed context|Nexus status|I need one more detail/i);
  });

  it.each([
    ['what car would you recommend', 'general_advisor'],
    ['what do you think about the Tesla Model 3', 'general_advisor'],
    ['can you build me a CRM for Nexus', 'nexus_build_planning'],
  ])('routes new advisory topic "%s" without AI-model keyword overfitting', async (message, expected) => {
    const response = await handleHermesMessage({ message });
    expect(response.route).toBe(expected);
    expect(response.usedSupabase).toBe(false);
    expect(response.text).not.toMatch(/token usage|model status|I need one more detail/i);
  });

  it('uses the Nexus revenue advisory contract and plan-level continuity only', async () => {
    const first = await handleHermesMessage({ message: 'what is the best money making opportunity available to me' });
    expect(first.route).toBe('revenue_reasoning');
    expect(first.text).toMatch(/\$97|next safe action/i);
    for (const message of ['is that realistic', 'what would stop us', 'how do we start this process', 'what should we do first']) {
      const follow = await handleHermesMessage({ message });
      expect(follow.route).toBe('advisory_followup');
      expect(follow.diagnostics.advisoryContinuityUsed).toBe(true);
      expect(follow.diagnostics.contextPacketSummary.selectionMemoryAttached).toBe(false);
      expect(follow.text).toMatch(/Source:|prior advisory context/i);
    }
  });

  it('renders system health from evidence instead of policy prose', async () => {
    const response = await handleHermesMessage({ message: 'how is the system health' });
    expect(response.route).toBe('system_health_report');
    expect(response.text).toMatch(/system is mostly healthy|local reports|next move/i);
    expect(response.text).not.toMatch(/Status summary:|Source checked:|Audit details|reports\//i);
    expect(response.text).not.toMatch(bannedStatus);
    expect(response.rememberedContext).toBe(false);
  });

  it('renders research engine status from report-backed evidence', async () => {
    const response = await handleHermesMessage({ message: 'is the research engine working' });
    expect(response.route).toBe('research_engine_status');
    expect(response.text).toMatch(/Configuration state:|Source checked:|Last known run\/report:|Blockers:|Next safe action:/i);
    expect(response.text).not.toMatch(bannedStatus);
  });

  it('attempts approval records without asking for a target', async () => {
    const response = await handleHermesMessage({ message: 'do i have any approvals that are pending' });
    expect(response.route).toBe('explicit_domain_retrieval');
    expect(response.text).toMatch(/approval|pending|queue|item/i);
    expect(response.text).not.toMatch(bannedStatus);
  });

  it('attempts client inventory without asking Ray to name a client', async () => {
    const response = await handleHermesMessage({ message: 'do we have any clients' });
    expect(response.route).toBe('client_records');
    expect(response.text).toMatch(/client|table|records/i);
    expect(response.text).not.toMatch(/Tell me the client|I need a concrete decision/i);
  });

  it('answers both natural provenance phrasings from provenance memory', async () => {
    await handleHermesMessage({ message: 'how is the system health' });
    for (const message of ['what did you get that last response from', 'what part of your decision making process did you use']) {
      const response = await handleHermesMessage({ message });
      expect(response.route).toBe('trace_source_meta');
      expect(response.text).toMatch(/route|intent/i);
      expect(response.text).toMatch(/Sources|context|Source:/i);
      expect(response.text).toMatch(/Confidence:/i);
      expect(response.text).not.toMatch(/I need one more detail|general recommendation, a Nexus build plan/i);
    }
  });

  it('keeps Ray Review, specialist handoff, and scheduling draft-only', async () => {
    const review = await handleHermesMessage({ message: 'create a Ray Review card for that' });
    expect(review.route).toBe('approval_action_prepare');
    expect(review.text).toMatch(/not.*(?:saved|submitted)|no eligible target/i);
    const handoff = await handleHermesMessage({ message: 'prepare specialist handoff' });
    expect(handoff.route).toBe('specialist_handoff');
    expect(handoff.text).toMatch(/Specialist lane:|Context included:|Missing:|Draft status:/i);
    expect(handoff.text).toMatch(/not.*(?:created|saved|assigned|sent)/i);
    const schedule = await handleHermesMessage({ message: 'schedule an audit' });
    expect(schedule.route).toBe('schedule_action_prepare');
    expect(schedule.text).toMatch(/draft|will not activate a scheduler/i);
    expect(schedule.text).not.toMatch(/scheduler was activated/i);
  });

  it('reserves selection memory for explicit item references', async () => {
    await handleHermesMessage({ message: 'what business opportunities are available' });
    for (const message of ['number 3', 'that one']) {
      const response = await handleHermesMessage({ message });
      expect(response.route).toBe('memory_followup');
      expect(response.diagnostics.contextPacketSummary.selectionMemoryAttached).toBe(true);
      expect(response.diagnostics.advisoryContinuityUsed).toBe(false);
    }
  });

  it('isolates selection and advisory state by tenant/session', async () => {
    await handleHermesMessage({ message: 'what business opportunities are available', tenantId: 'tenant-a', sessionId: 'session-a' });
    const other = await handleHermesMessage({ message: 'number 3', tenantId: 'tenant-b', sessionId: 'session-b' });
    expect(other.diagnostics.contextPacketSummary.selectionMemoryAttached).toBe(false);
    expect(other.text).toMatch(/no stored context item matched/i);
    await handleHermesMessage({ message: 'what is the best money making opportunity available to me', tenantId: 'tenant-a', sessionId: 'session-a' });
    const unrelated = await handleHermesMessage({ message: 'is that realistic', tenantId: 'tenant-b', sessionId: 'session-b' });
    expect(unrelated.route).toBe('fallback_clarification');
  });

  it('labels partial Supabase verification instead of implying completeness', () => {
    const text = renderRecordContract('approvals', {
      text: 'One table succeeded and one failed.', source: 'live_supabase_context', sourceType: 'live_supabase', liveData: true,
      timestamp: '2026-07-02T00:00:00Z', tablesQueried: ['task_requests', 'approvals'], rowCounts: { task_requests: 2, approvals: 0 },
      tableResults: { task_requests: { status: 'success', rowCount: 2 }, approvals: { status: 'error', rowCount: 0, error: 'RLS denied' } },
      verificationStatus: 'partial', blocker: 'approvals failed',
    });
    expect(text).toMatch(/partial verification|approvals failed/i);
    expect(text).not.toMatch(/full verification/i);
  });

  it('clear chat resets the active brain selection lane', async () => {
    await handleHermesMessage({ message: 'what business opportunities are available' });
    hermesStore.clearHistory();
    const response = await handleHermesMessage({ message: 'number 3' });
    expect(response.diagnostics.contextPacketSummary.selectionMemoryAttached).toBe(false);
  });

  it.each([
    ['pricing model for the offer'], ['business model for GoClear'],
  ])('does not classify "%s" as AI model usage', (message) => {
    expect(route(message).routeId).not.toBe('cost_model_usage_status');
  });
});
