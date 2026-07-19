import { describe, expect, it, beforeEach } from 'vitest';
import { buildHermesOperatingContext } from '../src/lib/hermes/hermesOperatingContext';
import { classifyHermesConversationMode } from '../src/lib/hermes/hermesModeClassifier';
import { runHermesConversation, resetHermesCanonicalConversationSession } from '../src/lib/hermes/hermesConversationEngine';
import { normalizeHermesWorkroomResponse } from '../src/lib/hermes/hermesWorkroomResponse';

const context = buildHermesOperatingContext(new Date('2026-07-18T12:00:00.000Z'));

describe('Hermes live Workroom contract', () => {
  beforeEach(() => resetHermesCanonicalConversationSession());

  it.each([
    'what should we focus on today?',
    'what should we do first?',
    'what needs my attention?',
    'where should we start?',
    'what is the top priority?',
    'give me today’s priorities',
    'what is the biggest problem right now?',
    'what should Nexus handle first?',
  ])('routes %s to executive priority advice', (message) => {
    expect(classifyHermesConversationMode(message).mode).toBe('EXECUTIVE_ADVICE');
  });

  it('answers today-priority questions from the visible operating context', () => {
    const result = runHermesConversation({
      message: 'what should we focus on today?',
      actorRole: 'admin',
      channel: 'full_workroom',
      pageContext: { operatingContext: context },
    });
    expect(result.mode).toBe('EXECUTIVE_ADVICE');
    expect(result.action).toBeNull();
    expect(result.contextUsed).toContain('operating_context_panel');
    expect(result.response).toMatch(/Focus first/i);
    expect(result.response).toMatch(/Client live-data flag off/i);
    expect(result.response).toMatch(/Stripe test completion|readiness review journey/i);
    expect(result.response).toMatch(/First step/i);
    expect(result.response).not.toMatch(/unknown context|concrete decision|general recommendation|category/i);
  });

  it('preserves multi-turn advisory memory from the operating-context recommendation', () => {
    let first = runHermesConversation({
      message: 'what should we focus on today?',
      actorRole: 'admin',
      channel: 'full_workroom',
      pageContext: { operatingContext: context },
    });
    const why = runHermesConversation({ message: 'why that one?', session: first.session, actorRole: 'admin', channel: 'full_workroom' });
    expect(why.mode).toBe('FOLLOW_UP_ADVICE');
    expect(why.response).toMatch(/Client live-data flag off|customer/i);
    first = why;
    const stop = runHermesConversation({ message: 'what would stop us?', session: first.session, actorRole: 'admin', channel: 'full_workroom' });
    expect(stop.mode).toBe('FOLLOW_UP_ADVICE');
    expect(stop.response).toMatch(/blockers|customer|dependency|risk/i);
    const deeper = runHermesConversation({ message: 'go deeper on number 2', session: stop.session, actorRole: 'admin', channel: 'full_workroom' });
    expect(deeper.response).toMatch(/Fake customer not inserted|Stripe test completion|readiness review journey|revenue/i);
  });

  it('normalizes canonical responses to serializable Workroom messages without callbacks', () => {
    const result = runHermesConversation({
      message: 'turn that one into a task',
      actorRole: 'admin',
      channel: 'full_workroom',
      pageContext: { operatingContext: context },
    });
    const normalized = normalizeHermesWorkroomResponse(result, { messageId: 'test-hermes' });
    expect(normalized).toMatchObject({ messageId: 'test-hermes', role: 'hermes' });
    expect(Array.isArray(normalized.actions)).toBe(true);
    expect(JSON.stringify(normalized)).not.toMatch(/onClick|function|password|secret|token/i);
    expect(() => JSON.parse(JSON.stringify(normalized))).not.toThrow();
  });
});
