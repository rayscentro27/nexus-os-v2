import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import fs from 'node:fs';
import { buildHermesOperatingContext } from '../src/lib/hermes/hermesOperatingContext';
import { runHermesConversation, resetHermesCanonicalConversationSession } from '../src/lib/hermes/hermesConversationEngine';
import { classifyHermesConversationMode } from '../src/lib/hermes/hermesModeClassifier';
import { hermesStore } from '../src/lib/hermesChatStore';

const context = buildHermesOperatingContext(new Date('2026-07-19T12:00:00.000Z'));

function similarity(a: string, b: string): number {
  const words = (value: string) => new Set(value.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter((word) => word.length > 3));
  const left = words(a);
  const right = words(b);
  const intersection = [...left].filter((word) => right.has(word)).length;
  const union = new Set([...left, ...right]).size || 1;
  return intersection / union;
}

function ask(message: string, session?: ReturnType<typeof runHermesConversation>['session']) {
  return runHermesConversation({
    message,
    session,
    actorRole: 'admin',
    channel: 'full_workroom',
    pageContext: { operatingContext: context },
  });
}

describe('Hermes production intent differentiation', () => {
  beforeEach(() => resetHermesCanonicalConversationSession());

  it('classifies priority, risk, and revenue as distinct executive intents', () => {
    expect(classifyHermesConversationMode('what should we focus on today?')).toMatchObject({ mode: 'EXECUTIVE_ADVICE', intent: 'executive_priority' });
    expect(classifyHermesConversationMode('what is our biggest risk right now?')).toMatchObject({ mode: 'EXECUTIVE_ADVICE', intent: 'executive_risk' });
    expect(classifyHermesConversationMode('how can we make money today?')).toMatchObject({ mode: 'EXECUTIVE_ADVICE', intent: 'revenue_action' });
  });

  it('answers priority, risk, and revenue with different strategies and concepts', () => {
    const priority = ask('what should we focus on today?');
    const risk = ask('what is our biggest risk right now?', priority.session);
    const revenue = ask('how can we make money today?', risk.session);

    expect(priority.responseStrategy).toBe('executive_priority_response');
    expect(risk.responseStrategy).toBe('executive_risk_response');
    expect(revenue.responseStrategy).toBe('revenue_action_response');

    expect(priority.response).toMatch(/Focus first|First step/i);
    expect(risk.response).toMatch(/biggest risk|mitigation|affected area/i);
    expect(revenue.response).toMatch(/fastest revenue action|\$97|Stripe stays test-only|offer/i);

    expect(priority.response).not.toMatch(/unknown context|concrete decision/i);
    expect(risk.response).not.toMatch(/Focus first/i);
    expect(revenue.response).not.toMatch(/Focus first|biggest risk is/i);
    expect(similarity(priority.response, risk.response)).toBeLessThan(0.72);
    expect(similarity(priority.response, revenue.response)).toBeLessThan(0.72);
  });

  it('answers rationale, feasibility, blocker, and deep-dive follow-ups from different memory fields', () => {
    const first = ask('what should we focus on today?');
    const rationale = ask('why that one?', first.session);
    const feasibility = ask('is that realistic?', rationale.session);
    const blockers = ask('what would stop us?', feasibility.session);
    const deepDive = ask('go deeper on number 2', blockers.session);

    expect(rationale.intent).toBe('followup_rationale');
    expect(feasibility.intent).toBe('followup_feasibility');
    expect(blockers.intent).toBe('followup_blockers');
    expect(deepDive.intent).toBe('followup_deep_dive');

    expect(rationale.responseStrategy).toBe('followup_rationale_response');
    expect(feasibility.responseStrategy).toBe('followup_feasibility_response');
    expect(blockers.responseStrategy).toBe('followup_blockers_response');
    expect(deepDive.responseStrategy).toBe('followup_deep_dive_response');

    expect(rationale.response).toMatch(/I chose|comes before/i);
    expect(feasibility.response).toMatch(/realistic|bounded scope/i);
    expect(blockers.response).toMatch(/concrete blockers|Mitigation/i);
    expect(deepDive.response).toMatch(/Going deeper|Dependencies|Next step/i);

    expect(rationale.response).not.toMatch(/Wave 4A corpus|source file|router/i);
    expect(feasibility.response).not.toMatch(/Wave 4A corpus|source file|router/i);
    expect(similarity(rationale.response, feasibility.response)).toBeLessThan(0.72);
    expect(similarity(feasibility.response, blockers.response)).toBeLessThan(0.72);
  });
});

describe('Hermes Workroom production render repair', () => {
  it('does not return scrollIntoView as a React effect cleanup', () => {
    const source = fs.readFileSync('src/components/HermesChatPanel.jsx', 'utf8');
    expect(source).not.toMatch(/useEffect\(\(\)\s*=>\s*end\.current\?\.scrollIntoView/);
    expect(source).toMatch(/typeof target\.scrollIntoView === 'function'/);
  });
});

describe('Hermes legacy persisted-message migration', () => {
  const storage = new Map<string, string>();

  beforeEach(() => {
    storage.clear();
    (globalThis as unknown as { window?: unknown }).window = {
      localStorage: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => { storage.set(key, value); },
        removeItem: (key: string) => { storage.delete(key); },
      },
    };
  });

  afterEach(() => {
    delete (globalThis as unknown as { window?: unknown }).window;
  });

  it('migrates legacy arrays into a schema envelope and drops unsafe action data', () => {
    storage.set('nexus_hermes_chat_history', JSON.stringify([
      { role: 'user', text: 'legacy question' },
      {
        role: 'hermes',
        text: 'legacy answer',
        workroomResponse: {
          messageId: 'legacy-hermes',
          role: 'hermes',
          text: 'legacy answer',
          mode: 'EXECUTIVE_ADVICE',
          intent: 'executive_priority',
          responseStrategy: 'executive_priority_response',
          evidenceState: 'REPORT_BACKED',
          confidence: 0.8,
          createdAt: '2026-07-19T12:00:00.000Z',
          actions: [
            { id: 'safe', type: 'DRAFT_RAY_REVIEW', label: 'Draft Ray Review request', enabled: true, requiresApproval: true },
            { id: 'bad', type: 'CALLBACK_FROM_STORAGE', label: 'Bad', enabled: true, requiresApproval: false, onClick: 'not-a-function' },
          ],
        },
      },
    ]));

    const loaded = hermesStore.getMessages();
    expect(loaded).toHaveLength(2);
    expect(loaded[1].workroomResponse?.actions).toHaveLength(1);
    expect(loaded[1].workroomResponse?.actions[0].type).toBe('DRAFT_RAY_REVIEW');
    const stored = JSON.parse(storage.get('nexus_hermes_chat_history') || '{}');
    expect(stored.schemaVersion).toBe(2);
    expect(JSON.stringify(stored)).not.toMatch(/onClick|CALLBACK_FROM_STORAGE|function/i);
  });
});
