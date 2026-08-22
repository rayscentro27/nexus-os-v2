import fs from 'node:fs';
import { describe, expect, it } from 'vitest';
import { classifyHermesConversationMode, normalizeHermesConversationText } from '../src/lib/hermes/hermesModeClassifier';
import { runHermesConversation } from '../src/lib/hermes/hermesConversationEngine';
import { buildHermesOperatingContext } from '../src/lib/hermes/hermesOperatingContext';
import { getTimeContext } from '../src/lib/hermesTimeContext';

describe('Hermes conversational front door', () => {
  it.each([
    'Good evening.',
    'Good evening, Nexus.',
    'Good evening Nexus',
    'Good evening, Hermes.',
    'Hello, Nexus.',
    'Hey Nexus!',
    'Morning Hermes.',
    'Good night, Nexus.',
  ])('classifies greeting %s as social conversation', (message) => {
    expect(classifyHermesConversationMode(message)).toMatchObject({ mode: 'SOCIAL_GREETING' });
  });

  it.each(['How are you, Nexus?', 'Thanks, Hermes.', 'Okay Nexus.', "What's up, Nexus?"])('classifies casual turn %s safely', (message) => {
    expect(classifyHermesConversationMode(message)).toMatchObject({ mode: 'CASUAL_CONVERSATION' });
  });

  it.each([
    'What should I focus on today?',
    'Nexus, what should I focus on today?',
    'What should we do today?',
    'What needs my attention?',
    'Give me my priorities for today.',
    "What's my highest priority?",
    'Good evening, Nexus. What should I focus on today?',
  ])('classifies priority request %s as executive advice', (message) => {
    expect(classifyHermesConversationMode(message)).toMatchObject({ mode: 'EXECUTIVE_ADVICE', intent: 'executive_priority' });
  });

  it('normalizes vocatives and punctuation without changing substantive Nexus content', () => {
    expect(normalizeHermesConversationText('Nexus, what should I focus on today?')).toBe('what should i focus on today');
    expect(normalizeHermesConversationText('Good evening, Nexus.')).toBe('good evening');
    expect(normalizeHermesConversationText('Hey, Nexus, what needs my attention?')).toBe('hey what needs my attention');
    expect(normalizeHermesConversationText('What is the Nexus architecture?')).toBe('what is the nexus architecture');
  });

  it('answers greetings through the canonical deterministic engine with current local time truth', () => {
    const result = runHermesConversation({ message: 'Good evening, Nexus.', actorRole: 'admin', channel: 'full_workroom' });
    const greeting = getTimeContext().timeOfDay === 'morning' ? 'Good morning' : getTimeContext().timeOfDay === 'afternoon' ? 'Good afternoon' : getTimeContext().timeOfDay === 'evening' ? 'Good evening' : 'Good night';
    expect(result.mode).toBe('SOCIAL_GREETING');
    expect(result.response).toContain(greeting);
    expect(result.response).not.toMatch(/insufficient|authorized context|Ray Review|system health/i);
    expect(result.action).toBeNull();
  });

  it('answers daily priorities from the canonical Hermes operating context', () => {
    const result = runHermesConversation({
      message: 'Nexus, what should I focus on today?',
      actorRole: 'admin',
      channel: 'full_workroom',
      pageContext: { operatingContext: buildHermesOperatingContext(new Date('2026-07-19T12:00:00.000Z')) },
    });
    expect(result.mode).toBe('EXECUTIVE_ADVICE');
    expect(result.intent).toBe('executive_priority');
    expect(result.responseStrategy).toBe('executive_priority_response');
    expect(result.response).toMatch(/Focus first|highest|priority/i);
    expect(result.response).not.toMatch(/insufficient|authorized context/i);
    expect(result.action).toBeNull();
  });

  it('keeps ambiguity and governance boundaries intact', () => {
    expect(classifyHermesConversationMode('Do that.').mode).toBe('CLARIFICATION_REQUIRED');
    expect(classifyHermesConversationMode('publish this').mode).toBe('CLARIFICATION_REQUIRED');
    expect(classifyHermesConversationMode('send the report').mode).toBe('CLARIFICATION_REQUIRED');
    expect(classifyHermesConversationMode('charge the customer').mode).not.toBe('SOCIAL_GREETING');
    expect(classifyHermesConversationMode('place a funded trade').mode).toBe('COMMAND');
  });

  it('keeps typed and voice-shaped text on the same Workroom canonical path before model-first', () => {
    const source = fs.readFileSync('src/components/HermesChatPanel.jsx', 'utf8');
    expect(source).toMatch(/onTranscript=\{\(text\) => send\(text\)\}/);
    expect(source.indexOf('const classification = classifyHermesConversationMode(clean)')).toBeGreaterThan(-1);
    expect(source.indexOf('const classification = classifyHermesConversationMode(clean)')).toBeLessThan(source.indexOf('const modelFirstResult = await runHermesModelFirstConversation'));
    expect(source).toMatch(/text: clean/);
  });
});
