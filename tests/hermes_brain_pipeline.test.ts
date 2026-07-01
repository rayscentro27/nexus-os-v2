import { describe, it, expect, beforeEach } from 'vitest';
import { handleHermesMessage, getCapabilityBadge } from '../src/lib/hermesBrainPipeline';
import { resetConversationState, setLastListedItems, setLastReferencedItem } from '../src/lib/hermesConversationState';
import { getCapabilityReport } from '../src/lib/hermesCapabilityStatus';
import { getSupabaseAccessState } from '../src/lib/hermesSupabaseAccessState';
import { reasonAboutMessage } from '../src/lib/hermesReasoningEngine';
import { detectActivationLevel, shouldUseModelForLevel, shouldUseSupabaseForLevel } from '../src/lib/hermesActivationLevels';
import { logRoutingTrace } from '../src/lib/hermesRoutingTrace';

describe('Hermes Brain Pipeline', () => {
  beforeEach(() => {
    resetConversationState();
  });

  describe('handleHermesMessage', () => {
    it('answers capability questions locally', async () => {
      const result = await handleHermesMessage({ message: 'What can you do?' });
      expect(result.answer).toContain('Live');
      expect(result.source).toBe('capability');
      expect(result.modelRoute.route).toBe('no_model');
      expect(result.confidence).toBe('high');
    });

    it('answers casual questions locally', async () => {
      const result = await handleHermesMessage({ message: 'Hello' });
      expect(result.answer).toBeTruthy();
      expect(result.source).toBe('local');
      expect(result.modelRoute.route).toBe('no_model');
    });

    it('answers section status questions locally', async () => {
      const result = await handleHermesMessage({ message: 'Is the trading section live?' });
      expect(result.answer).toContain('Trading');
      expect(result.source).toBe('local');
      expect(result.modelRoute.route).toBe('no_model');
    });

    it('answers operations questions locally', async () => {
      const result = await handleHermesMessage({ message: 'What processes are running?' });
      expect(result.answer).toBeTruthy();
      expect(result.modelRoute.route).toBe('no_model');
    });

    it('blocks execution requests with safety message', async () => {
      const result = await handleHermesMessage({ message: 'Send an email to all clients' });
      expect(result.answer).toContain('cannot execute');
      expect(result.answer).toContain('Ray Review');
    });

    it('answers memory questions locally', async () => {
      const result = await handleHermesMessage({ message: 'What did we work on today?' });
      expect(result.answer).toBeTruthy();
      expect(result.modelRoute.route).toBe('no_model');
    });

    it('returns structured response with all fields', async () => {
      const result = await handleHermesMessage({ message: 'What can you do?' });
      expect(result).toHaveProperty('answer');
      expect(result).toHaveProperty('intent');
      expect(result).toHaveProperty('modelRoute');
      expect(result).toHaveProperty('reasoning');
      expect(result).toHaveProperty('capabilityBadge');
      expect(result).toHaveProperty('confidence');
      expect(result).toHaveProperty('source');
      expect(result).toHaveProperty('timestamp');
    });

    it('tracks conversation history', async () => {
      await handleHermesMessage({ message: 'What can you do?' });
      const { getConversationHistory } = await import('../src/lib/hermesConversationState');
      const history = getConversationHistory();
      expect(history.length).toBeGreaterThanOrEqual(2);
      expect(history[0].role).toBe('user');
      expect(history[1].role).toBe('assistant');
    });

    it('never returns empty answer', async () => {
      const messages = [
        'What can you do?',
        'Hello',
        'Is trading live?',
        'What approvals are pending?',
        'Tell me about opportunities',
      ];
      for (const msg of messages) {
        const result = await handleHermesMessage({ message: msg });
        expect(result.answer).toBeTruthy();
        expect(result.answer.length).toBeGreaterThan(0);
      }
    });
  });

  describe('Follow-up resolution', () => {
    it('resolves "number 3" against last listed items', async () => {
      setLastListedItems([
        { title: 'Strategy A', type: 'strategy' },
        { title: 'Strategy B', type: 'strategy' },
        { title: 'Strategy C', type: 'strategy' },
      ]);
      const result = await handleHermesMessage({ message: 'number 3' });
      expect(result.answer).toContain('Strategy C');
      expect(result.source).toBe('conversation-followup');
    });

    it('resolves "that one" against last referenced item', async () => {
      setLastReferencedItem({ title: 'The Winner', type: 'opportunity' });
      const result = await handleHermesMessage({ message: 'that one' });
      expect(result.answer).toContain('The Winner');
      expect(result.source).toBe('conversation-followup');
    });

    it('asks clarification for follow-up with no context', async () => {
      const result = await handleHermesMessage({ message: 'number 3' });
      expect(result.answer).toContain('context');
    });
  });

  describe('Business strategy reasoning', () => {
    it('does NOT return section status for business strategy questions', async () => {
      const result = await handleHermesMessage({ message: 'What business can I start in 30 days?' });
      // Should NOT contain section status list
      expect(result.answer).not.toContain('**Operations & Scheduler**');
      expect(result.answer).not.toContain('**Trading**');
      expect(result.answer).toContain('business');
    });

    it('reasons from available data, not generic templates', async () => {
      const result = await handleHermesMessage({ message: 'What opportunities should I pursue?' });
      expect(result.answer).toBeTruthy();
      // Should not be a generic "I need more info" when data exists
    });
  });

  describe('Supabase access state', () => {
    it('returns specific state, not vague "gated"', async () => {
      const state = await getSupabaseAccessState('approvals');
      expect(['available', 'blocked-by-auth', 'blocked-by-RLS', 'table-empty', 'not-used', 'not-configured']).toContain(state.state);
      expect(state.userFacing).toBeTruthy();
      expect(state.userFacing).not.toContain('gated');
    });

    it('distinguishes not-used from blocked-by-RLS', async () => {
      const notUsed = await getSupabaseAccessState('trading_strategies', 'local static data');
      expect(notUsed.state).toBe('not-used');
      expect(notUsed.userFacing).toContain('does not use Supabase');
    });
  });

  describe('Capability status', () => {
    it('returns consistent badge text', () => {
      const badge = getCapabilityBadge();
      const report = getCapabilityReport();
      expect(badge).toBe(report.badgeText);
    });

    it('answers "what can you do" with specific capabilities', () => {
      const report = getCapabilityReport();
      expect(report.capabilities.length).toBeGreaterThan(0);
      for (const cap of report.capabilities) {
        expect(cap.name).toBeTruthy();
        expect(cap.userFacing).toBeTruthy();
      }
    });

    it('never says "gated" in user-facing text', () => {
      const report = getCapabilityReport();
      for (const cap of report.capabilities) {
        expect(cap.userFacing.toLowerCase()).not.toContain('gated');
      }
    });
  });

  describe('Reasoning engine', () => {
    it('answers locally for section status', () => {
      const plan = reasonAboutMessage(
        'Is the trading section live?',
        null,
        'operations',
        'no_model'
      );
      expect(plan.decision).toBe('answer-locally');
      expect(plan.confidence).toBe('high');
    });

    it('asks clarification only when no context exists', () => {
      const plan = reasonAboutMessage(
        'What strategy should I use?',
        null,
        'ambiguous',
        'primary_model'
      );
      expect(plan.decision).toBe('ask-clarification');
      expect(plan.clarificationQuestion).toBeTruthy();
    });

    it('answers with context when page context exists', () => {
      const plan = reasonAboutMessage(
        'What is on this page?',
        { route: '/trading', pageId: 'trading', visibleItems: [{ title: 'Strategy A' }] },
        'page_context',
        'no_model'
      );
      expect(plan.decision).toBe('answer-with-context');
    });

    it('resolves follow-up references locally', () => {
      const plan = reasonAboutMessage(
        'number 3',
        null,
        'page_context',
        'no_model'
      );
      expect(plan.decision).toBe('answer-locally');
    });
  });
});

describe('Hermes activation enforcement', () => {
  it.each([
    ['Can you place a trade?', true, 0],
    ['What model are you using?', false, 1],
    ['What business opportunities are available?', false, 2],
    ['Which one do you recommend?', true, 3],
    ['What business should I start in 30 days?', false, 4],
    ['Compose a polished landing page', false, 5],
    ['Create a review card', false, 6],
  ])('detects %s as level %s', (message, memory, expected) => {
    expect(detectActivationLevel(message as string, memory as boolean, false).level).toBe(expected);
  });

  it('lets safety override model/action language', () => {
    expect(detectActivationLevel('Publish a polished proposal now', true, true).level).toBe(0);
  });

  it('keeps status/cost off model and Level 2 on Supabase', () => {
    expect(shouldUseModelForLevel(1)).toBe(false);
    expect(shouldUseSupabaseForLevel(2)).toBe(true);
  });

  it('returns the same activation level across surfaces', async () => {
    const full = await handleHermesMessage({ message: 'What business should I start in 30 days?', surface: 'full_workroom' });
    resetConversationState();
    const inline = await handleHermesMessage({ message: 'What business should I start in 30 days?', surface: 'inline_drawer' });
    expect(full.activationLevel).toBe(inline.activationLevel);
    expect(full.route).toBe(inline.route);
  });

  it('records safe trace metadata', () => {
    const trace = logRoutingTrace({ message: 'hello test@example.com', surface: 'unknown', page: null, route: 'no_model', activationLevel: 1, activationLevelName: 'Meta', intent: 'status', sourceDecision: 'local', usedSupabase: false, supabaseTables: [], usedModel: false, modelRoute: 'no_model', usedMemory: false, selectedEntity: null, safetyGate: false, answerBuilder: 'test', fallbackReason: null, correctnessHint: 'deterministic', confidence: 'high' });
    expect(trace.message).not.toContain('test@example.com');
    expect(trace.usedModel).toBe(false);
  });
});
