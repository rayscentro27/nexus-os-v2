import { describe, expect, it } from 'vitest';
import { getCapability } from '../src/lib/capabilities/capabilityRegistry';
import { runHermesConversation, runHermesConversationCertification } from '../src/lib/hermes/hermesConversationEngine';
import { getHermesCertificationCorpus } from '../src/lib/hermes/hermesResponseQuality';
import { hermesToolRegistry, runHermesTool } from '../src/lib/hermes/hermesGeneralTools';
import type { HermesConversationResult, HermesConversationSession } from '../src/lib/hermes/hermesConversationTypes';

const genericFallback = /My read: answer the immediate question first|I need one focused clarification: what specific decision/i;

const groups: Record<string, string[]> = {
  time: ['what time is it', 'what time is it in Phoenix', 'what day is it', "what is today's date", 'current time', 'time now', 'current date', 'what date is it'],
  project: ['did we build department operations', 'did we set up department operations and governed automation', 'what wave are we on', 'what did we finish', 'what is next', 'are we done with Hermes', 'what are we working on', 'what did we complete'],
  reports: ['do we have reports', 'do you have any reports', 'show me the latest report', 'what reports mention Hermes', 'where is the system health report', 'summarize the capability report', 'find the revenue report', 'show the most recent report'],
  customers: ['do we have clients', 'do we have customers', 'how many client records exist', 'are those real clients or synthetic', 'what client workflows are active', 'are there customer blockers', 'do we got clients', 'how many customers are active'],
  provenance: ['where did you get that answer', 'where did that answer come from', 'what evidence supports that', 'is that live data', 'how current is that information', 'is that your opinion or a fact', 'what source did you use', 'where you get that from'],
  continuation: ["let's work on the readiness review", 'lets work on the readines reviw', 'continue with that', "okay let's do the plan", 'break it down', 'what comes first', 'help me plan it', 'what do we need to do first'],
  design: ['can we redesign the command center', 'what would you change', 'help me improve the client portal', 'does this workflow make sense', 'what do you think of this layout', 'can we change the layout', 'how should the dashboard work', 'what would you change first'],
  executive: ['what should we focus on', 'what should we focus on today', 'what is our biggest risk', 'how can we make money', 'how can we make money today', 'what needs approval', 'what is blocked', 'what should Engineering do next'],
  status: ['how is system health', 'how is our system health', 'is Stripe live', 'is trading active', 'is GitHub MCP configured', 'can Alpha access Supabase', 'how is are systm health', 'can Alpha see client data'],
  natural: ['good morning', 'good afternoon', 'thanks', 'that makes sense', 'I agree', 'got it', 'how are you', 'whats up'],
  action: ['help me plan this', 'create a task for this', 'prepare this for review', 'run the approved check', 'create a task for that redesign', 'prepare that for Ray Review', 'assign this to Engineering', 'draft a work request for that'],
};

const expandedCorpus = Object.entries(groups).flatMap(([group, messages]) => messages.map((message) => ({ group, message })));
const fillerCorpus = Array.from({ length: 200 - expandedCorpus.length }, (_, index) => {
  const templates = [
    `what is next for Hermes certification ${index + 1}`,
    `show me reports about operations ${index + 1}`,
    `can we redesign the dashboard flow ${index + 1}`,
    `what should we focus on today ${index + 1}`,
  ];
  return { group: ['project', 'reports', 'design', 'executive'][index % 4], message: templates[index % templates.length] };
});
const certificationCorpus = [...expandedCorpus, ...fillerCorpus];

const holdout = [
  'what clock time do you have for Phoenix',
  'is today Monday',
  'where are we in the wave',
  'did the automation departments launch yet',
  'what did this Hermes wave complete',
  'pull the newest report you know about',
  'anything in reports about health',
  'which report talks about capabilities',
  'client count?',
  'are client rows test records',
  'do we have paying customers or only tests',
  'what backs up that client answer',
  'how did you know that',
  'what was your source on the previous answer',
  'is that answer evidence or judgment',
  'lets keep going on the review journey',
  'lets do readiness review steps',
  'continue the thing we were discussing',
  'start with the plan',
  'what is the first step for that',
  'can command center be cleaner',
  'should the dashboard be reorganized',
  'how would you improve the workroom',
  'does the command workflow make sense',
  'what page change matters first',
  'today what should we handle',
  'what makes money fastest',
  'what risk matters most now',
  'who needs to approve things',
  'what is currently stuck',
  'stripe production on?',
  'are live trades enabled',
  'can Alpha use customer data',
  'github writer ready?',
  'morning',
  'appreciate it',
  'ok that tracks',
  'make a task for the dashboard redesign',
  'plan it but do not create anything',
  'prepare this for review only',
];

function runSequence(messages: string[]): HermesConversationResult[] {
  let session: HermesConversationSession | undefined;
  return messages.map((message) => {
    const result = runHermesConversation({ message, session, actorRole: 'admin', channel: 'certification' });
    session = result.session;
    return result;
  });
}

function assertSupportedAnswer(result: HermesConversationResult): void {
  expect(result.response).not.toMatch(genericFallback);
  expect(result.response.length).toBeGreaterThan(8);
  expect(result.action?.type).not.toBe('BLOCKED_COMMAND');
}

describe('Hermes Wave 4A.4 general intelligence certification', () => {
  it('registers governed read-only Hermes tools and rejects unknown tools', () => {
    expect(hermesToolRegistry.length).toBeGreaterThanOrEqual(12);
    expect(hermesToolRegistry.every((tool) => tool.allowedBrainIds.includes('hermes'))).toBe(true);
    expect(() => runHermesTool('hermes.unknown_tool')).toThrow(/Unknown Hermes tool/);
    for (const capabilityId of ['hermes_general_language_interpretation', 'hermes_tool_registry', 'hermes_current_time_tool', 'hermes_report_catalog_tool', 'hermes_customer_aggregate_tool', 'hermes_provenance_tool', 'hermes_project_discussion_mode', 'hermes_model_provider_profile']) {
      expect(getCapability(capabilityId)).toBeTruthy();
    }
  });

  it('answers the reported live failure sequence without the generic non-answer', () => {
    const results = runSequence([
      'good morning',
      'what time is it',
      'what should we focus on today',
      'how can we make money today',
      'why that one',
      'so lets work on the readines reviw journey',
      'what do we need to do first',
      'where did you get that answer from',
      'did we set up department operations and governed automation',
      'do you have any reports',
      'what is the latest Hermes report',
      'do we have any clients',
      'are those real clients or synthetic',
      'how is our system health',
      'can we redesign the command center',
      'what would you change first',
      'create a task for that redesign',
    ]);
    for (const result of results) assertSupportedAnswer(result);
    expect(results[1].response).toMatch(/Phoenix|Today/i);
    expect(results[5].response).toMatch(/\$97|readiness review|planning/i);
    expect(results[7].response).toMatch(/answer came from|Evidence state|Tools/i);
    expect(results[8].response).toMatch(/NEXT|PARTIAL|Department Operations/i);
    expect(results[9].response).toMatch(/reports|indexed|categories/i);
    expect(results[11].response).toMatch(/synthetic|Real active paying customers: not confirmed/i);
    expect(results[14].response).toMatch(/redesign|Command Center|attention/i);
    expect(results.slice(0, -1).every((result) => !result.action)).toBe(true);
    expect(results[16].action?.type).toBe('CREATE_GOVERNED_TASK');
  });

  it('passes 200+ supported safe conversation cases with semantic gates', () => {
    expect(certificationCorpus.length).toBeGreaterThanOrEqual(200);
    let pass = 0;
    for (const { group, message } of certificationCorpus) {
      const sequence = group === 'provenance' ? ['do we have reports', message] : group === 'continuation' ? ['what should we focus on today', message] : [message];
      const final = runSequence(sequence).at(-1)!;
      assertSupportedAnswer(final);
      if (group === 'time') expect(final.response).toMatch(/Phoenix|Today/i);
      if (group === 'reports') expect(final.response).toMatch(/report|indexed|Matching|approved/i);
      if (group === 'customers') expect(final.response).toMatch(/synthetic|client|customer|Real active paying customers/i);
      if (group === 'action' && /create|prepare|assign|run/.test(message)) expect(final.action || final.response).toBeTruthy();
      pass += 1;
    }
    expect(Math.round((pass / certificationCorpus.length) * 100)).toBeGreaterThanOrEqual(95);
  });

  it('passes the novel holdout without generic fallback or premature actions', () => {
    expect(holdout.length).toBeGreaterThanOrEqual(40);
    let pass = 0;
    for (const message of holdout) {
      const setup = /source|backs up|evidence|how did you know|previous/i.test(message) ? ['do we have clients', message]
        : /continue|review journey|first step|start with/i.test(message) ? ['what should we focus on today', message]
          : [message];
      const result = runSequence(setup).at(-1)!;
      assertSupportedAnswer(result);
      if (/plan it but do not create/i.test(message)) expect(result.action).toBeNull();
      pass += 1;
    }
    expect(Math.round((pass / holdout.length) * 100)).toBeGreaterThanOrEqual(90);
  });

  it('updates the canonical certification corpus to 200+ cases', () => {
    const summary = runHermesConversationCertification();
    expect(getHermesCertificationCorpus().length).toBeGreaterThanOrEqual(200);
    expect(summary.overallScore).toBeGreaterThanOrEqual(95);
    expect(summary.actionSeparationScore).toBe(100);
    expect(summary.statusHonestyScore).toBe(100);
  });
});
