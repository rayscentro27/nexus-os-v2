import { beforeEach, describe, expect, it } from 'vitest';
import { handleHermesMessage } from '../src/lib/hermesBrainPipeline';
import { resetConversationState } from '../src/lib/hermesConversationState';
import { routeHermesPriority } from '../src/lib/hermesPriorityRouter';
import { getSelectionMemory, setHermesMemoryScope } from '../src/lib/hermesMemoryStores';
import { buildIntentFrame } from '../src/lib/hermesIntentClassifier';
import { getActiveSession, clearSession } from '../src/lib/hermesAdvisorSession';
import { getSourceAuthorityForDomain, getSourceAuthorityLabel } from '../src/lib/hermesSourceAuthority';

const bannedPhrases = /I need one more detail: what specific outcome|I can reason from the allowed|I need a concrete decision|no eligible target was resolved|client_profiles: not verified/i;
const route = (message: string) => routeHermesPriority({ message, selectionMemory: getSelectionMemory() });

describe('Hermes Intent Frame — classification', () => {
  it.each([
    ['good morning', 'greeting', 'general_conversation'],
    ['where did you get that answer from', 'trace_question', 'trace'],
    ['how is the system health', 'status_question', 'system_health'],
    ['do i have any approvals that are pending', 'record_lookup', 'approvals'],
    ['do we have any clients', 'record_lookup', 'clients'],
    ['pull up the business opportunity report', 'domain_review', 'business_opportunities'],
    ['create a Ray Review card for that', 'approval_action_draft', 'approvals'],
    ['what can you do', 'brain_capability_status', 'general_conversation'],
    ['can you see what is on this page', 'page_context', 'current_page'],
    ['what was the score on the soccer game last night', 'external_current_info', 'external_info'],
  ])('classifies "%s" as intent=%s domain=%s', (message, expectedIntent, expectedDomain) => {
    const frame = buildIntentFrame(message);
    expect(frame.intent).toBe(expectedIntent);
    expect(frame.domain).toBe(expectedDomain);
  });

  it('detects safety disposition for risky actions', () => {
    const frame = buildIntentFrame('publish the report now');
    expect(frame.safetyDisposition).toBe('blocked');
  });

  it('detects approval-required disposition for draft actions', () => {
    const frame = buildIntentFrame('create a Ray Review card for that');
    expect(frame.safetyDisposition).toBe('approval_required');
  });

  it('detects follow-up context', () => {
    const frame = buildIntentFrame('how can we improve it');
    expect(frame.isFollowup).toBe(true);
  });

  it('detects named targets', () => {
    const frame = buildIntentFrame('create a Ray Review card for the $97 Credit & Funding Readiness Review');
    expect(frame.target.type).toBe('named_offer');
    expect(frame.target.label).toContain('$97');
  });

  it('detects ranked targets', () => {
    const frame = buildIntentFrame('what is the top business opportunity');
    expect(frame.target.type).toBe('ranked_item');
    expect(frame.target.rank).toBe(1);
  });
});

describe('Hermes Source Authority — contract', () => {
  it('returns correct source authority for business opportunities', () => {
    const authority = getSourceAuthorityForDomain('business_opportunities');
    expect(authority.levels).toContain('live_supabase');
    expect(authority.levels).toContain('static_context');
  });

  it('returns correct source authority for clients', () => {
    const authority = getSourceAuthorityForDomain('clients');
    expect(authority.levels).toContain('live_supabase');
    expect(authority.levels).not.toContain('static_context');
  });

  it('provides correct source label', () => {
    const label = getSourceAuthorityLabel('live_supabase');
    expect(label).toContain('live Supabase');
  });
});

describe('Hermes Advisor Session — business opportunity review', () => {
  beforeEach(() => {
    setHermesMemoryScope('test-session:default');
    resetConversationState();
    clearSession('test-session:default');
  });

  it('starts a review session and returns structured response', async () => {
    const response = await handleHermesMessage({
      message: 'pull up the business opportunity report and lets review each new opportunity',
      tenantId: 'test-session',
      sessionId: 'default',
    });
    expect(response.intentFrame?.intent).toBe('domain_review');
    expect(response.intentFrame?.domain).toBe('business_opportunities');
    expect(response.activeSession).toBeTruthy();
    expect(response.activeSession?.activeMode).toBe('business_opportunity_review');
    expect(response.activeSession?.activeList).toBeTruthy();
    expect(response.activeSession?.activeList?.length).toBeGreaterThan(0);
    expect(response.voiceReady).toBeTruthy();
    expect(response.voiceReady?.plainAnswer).toBeTruthy();
  });

  it('explains score from active session', async () => {
    await handleHermesMessage({
      message: 'pull up the business opportunity report',
      tenantId: 'test-session',
      sessionId: 'default',
    });
    const response = await handleHermesMessage({
      message: 'why did it get that score',
      tenantId: 'test-session',
      sessionId: 'default',
    });
    expect(response.intentFrame?.action).toBe('explain_score');
    expect(response.text).toContain('score');
  });

  it('provides improvement suggestions from active session', async () => {
    await handleHermesMessage({
      message: 'pull up the business opportunity report',
      tenantId: 'test-session',
      sessionId: 'default',
    });
    const response = await handleHermesMessage({
      message: 'how can we improve it',
      tenantId: 'test-session',
      sessionId: 'default',
    });
    expect(response.intentFrame?.action).toBe('improve');
    expect(response.text).toMatch(/improve|strengthen|enhance/i);
  });

  it('creates Ray Review draft for named target', async () => {
    const response = await handleHermesMessage({
      message: 'create a Ray Review card for the $97 Credit & Funding Readiness Review',
      tenantId: 'test-session',
      sessionId: 'default',
    });
    expect(response.text).toContain('$97 Credit & Funding Readiness Review');
    expect(response.text).toContain('not been saved');
    expect(response.text).not.toMatch(bannedPhrases);
  });

  it('does not ask what "it" means when session is active', async () => {
    await handleHermesMessage({
      message: 'pull up the business opportunity report',
      tenantId: 'test-session',
      sessionId: 'default',
    });
    const response = await handleHermesMessage({
      message: 'how can we improve it',
      tenantId: 'test-session',
      sessionId: 'default',
    });
    expect(response.text).not.toMatch(/what specific outcome|what.*it mean/i);
  });
});

describe('Hermes Client Source Attribution — fix', () => {
  beforeEach(() => {
    setHermesMemoryScope('default:default');
    resetConversationState();
  });

  it('does not show contradictory blocker when client_profiles succeeds with 0 rows', async () => {
    const response = await handleHermesMessage({ message: 'do we have any clients' });
    expect(response.route).toBe('client_records');
    expect(response.text).toMatch(/Source checked:.*client_profiles/i);
    expect(response.text).not.toMatch(/client_profiles: not verified/i);
  });
});

describe('Hermes Trace/Decision Process — route', () => {
  beforeEach(() => {
    setHermesMemoryScope('default:default');
    resetConversationState();
  });

  it('routes trace questions correctly', async () => {
    const response = await handleHermesMessage({ message: 'what part of your decision process did you use' });
    expect(response.route).toBe('trace_source_meta');
    expect(response.text).toMatch(/route|intent|source/i);
    expect(response.text).not.toMatch(bannedPhrases);
  });

  it('routes "was that live or local" correctly', async () => {
    const response = await handleHermesMessage({ message: 'was that live or local' });
    expect(response.route).toBe('trace_source_meta');
  });
});

describe('Hermes Voice-Ready Response — contract', () => {
  beforeEach(() => {
    setHermesMemoryScope('default:default');
    resetConversationState();
  });

  it('provides voice-ready response for system health', async () => {
    const response = await handleHermesMessage({ message: 'how is the system health' });
    expect(response.voiceReady).toBeTruthy();
    expect(response.voiceReady?.plainAnswer).toBeTruthy();
    expect(response.voiceReady?.plainAnswer.length).toBeGreaterThan(20);
  });

  it('provides voice-ready response for business opportunity review', async () => {
    const response = await handleHermesMessage({
      message: 'pull up the business opportunity report',
      tenantId: 'voice-test',
      sessionId: 'default',
    });
    expect(response.voiceReady).toBeTruthy();
    expect(response.voiceReady?.plainAnswer).toBeTruthy();
  });
});

describe('Hermes Preserved Behaviors — no regressions', () => {
  beforeEach(() => {
    setHermesMemoryScope('default:default');
    resetConversationState();
  });

  it('preserves live approvals Supabase lookup', async () => {
    const response = await handleHermesMessage({ message: 'do i have any approvals that are pending' });
    expect(response.route).toBe('explicit_domain_retrieval');
    expect(response.text).toMatch(/Source checked:.*task_requests and approvals/i);
  });

  it('preserves selection memory for number references', async () => {
    await handleHermesMessage({ message: 'what business opportunities are available' });
    const response = await handleHermesMessage({ message: 'number 3' });
    expect(response.route).toBe('memory_followup');
  });

  it('preserves specialist agent inventory', async () => {
    const response = await handleHermesMessage({ message: 'do we have a credit specialist agent' });
    expect(response.route).toBe('specialist_agent_inventory');
  });

  it('preserves page context route', async () => {
    const response = await handleHermesMessage({ message: 'what page are we on' });
    expect(response.route).toMatch(/page_context_status|page_connection_status/);
  });

  it('preserves system health route', async () => {
    const response = await handleHermesMessage({ message: 'how is the system health' });
    expect(response.route).toBe('system_health_report');
  });

  it('preserves research status route', async () => {
    const response = await handleHermesMessage({ message: 'is the research engine working' });
    expect(response.route).toBe('research_engine_status');
  });

  it('preserves safety gate', async () => {
    const response = await handleHermesMessage({ message: 'publish the report now' });
    expect(response.route).toBe('safety_gate');
    expect(response.text).toMatch(/cannot execute|blocked/i);
  });

  it('preserves Tesla Model 3 as new-topic boundary', async () => {
    const response = await handleHermesMessage({ message: 'what do you think about the Tesla Model 3' });
    expect(response.route).toBe('general_advisor');
  });
});
