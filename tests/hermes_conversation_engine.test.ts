import { describe, expect, it, beforeEach } from 'vitest';
import { classifyHermesConversationMode } from '../src/lib/hermes/hermesModeClassifier';
import { createHermesConversationSession } from '../src/lib/hermes/hermesMemoryResolver';
import { runHermesConversation, resetHermesCanonicalConversationSession } from '../src/lib/hermes/hermesConversationEngine';

describe('Hermes canonical conversation engine', () => {
  beforeEach(() => resetHermesCanonicalConversationSession());

  it.each([
    ['good morning', 'SOCIAL_GREETING'],
    ['how did you sleep', 'CASUAL_CONVERSATION'],
    ['what should we work on first', 'EXECUTIVE_ADVICE'],
    ['is Stripe live', 'SYSTEM_STATUS'],
    ['turn number 2 into a work request', 'TASK_REQUEST'],
    ['prepare that for Ray Review', 'APPROVAL_REQUEST'],
    ['enable live trading', 'COMMAND'],
  ])('classifies %s as %s', (message, mode) => {
    expect(classifyHermesConversationMode(message, true).mode).toBe(mode);
  });

  it('answers greetings naturally without operational menus', () => {
    const response = runHermesConversation({ message: 'good morning', actorRole: 'admin', channel: 'test' });
    expect(response.mode).toBe('SOCIAL_GREETING');
    expect(response.response).toMatch(/Good morning, Ray/);
    expect(response.response).not.toMatch(/Ray Review|system health|human tastes|lived experiences/i);
    expect(response.action).toBeNull();
  });

  it('keeps page context from dominating casual conversation', () => {
    const response = runHermesConversation({
      message: 'good night',
      actorRole: 'admin',
      channel: 'test',
      pageId: 'client-credit-profile',
      pageContext: { heading: 'Credit Profile', status: 'blocked' },
    });
    expect(response.mode).toBe('SOCIAL_GREETING');
    expect(response.response).toMatch(/Good night, Ray/);
    expect(response.response).not.toMatch(/credit|blocked|menu/i);
  });

  it('preserves advisory continuity for realistic follow-ups', () => {
    let session = createHermesConversationSession({ sessionId: 'advice', channel: 'test' });
    const first = runHermesConversation({ message: 'what should we work on first', session, actorRole: 'admin' });
    session = first.session;
    const followup = runHermesConversation({ message: 'is that realistic', session, actorRole: 'admin' });
    expect(followup.mode).toBe('FOLLOW_UP_ADVICE');
    expect(followup.memoryUsed).toContain('advisory_memory');
    expect(followup.response).toMatch(/realistic|bounded/i);
    expect(followup.action).toBeNull();
  });

  it('resolves numbered and named references against the latest advisory context', () => {
    let session = createHermesConversationSession({ sessionId: 'selection', channel: 'test' });
    session = runHermesConversation({ message: 'what should we work on first', session, actorRole: 'admin' }).session;
    const second = runHermesConversation({ message: 'number 2', session, actorRole: 'admin' });
    expect(second.mode).toBe('SELECTION_REFERENCE');
    expect(second.referencesResolved).toContain('department_operations_queue');
    expect(second.response).toMatch(/Department Operations/i);
  });

  it('separates questions from governed actions', () => {
    let session = createHermesConversationSession({ sessionId: 'actions', channel: 'test' });
    const advice = runHermesConversation({ message: 'what should we do first', session, actorRole: 'admin' });
    expect(advice.action).toBeNull();
    session = advice.session;
    const action = runHermesConversation({ message: 'turn number 2 into a work request', session, actorRole: 'admin' });
    expect(action.mode).toBe('TASK_REQUEST');
    expect(action.action).toMatchObject({ type: 'CREATE_GOVERNED_TASK', requiresApproval: true });
    expect(action.response).toMatch(/conversation-only|nothing has been saved|requires/i);
  });

  it('answers system status honestly', () => {
    expect(runHermesConversation({ message: 'is Stripe live' }).response).toMatch(/test mode|deferred/i);
    expect(runHermesConversation({ message: 'is trading active' }).response).toMatch(/blocked by policy/i);
    expect(runHermesConversation({ message: 'can Alpha see client data' }).response).toMatch(/not allowed|client PII/i);
    expect(runHermesConversation({ message: 'is GitHub MCP active' }).response).toMatch(/not configured|Writer access is disabled/i);
  });

  it('emits sanitized trace and quality evidence', () => {
    const response = runHermesConversation({ message: 'how is the system' });
    expect(response.trace).toMatchObject({ provider: 'nexus_native', actionDetected: false });
    expect(response.quality?.overallScore).toBeGreaterThanOrEqual(88);
    expect(JSON.stringify(response.trace)).not.toMatch(/password|secret|token/i);
  });
});
