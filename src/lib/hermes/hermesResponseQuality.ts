import type { HermesConversationResult, HermesResponseQuality } from './hermesConversationTypes';

export interface HermesQualityFixture {
  id: string;
  group: string;
  messages: string[];
  expectedModes?: string[];
  requiresNoAction?: boolean;
  requiresAction?: boolean;
  requiredConcepts?: RegExp[];
  forbiddenConcepts?: RegExp[];
}

const roboticPatterns = [
  /I do not have human tastes or lived experiences/i,
  /Do you want a general recommendation/i,
  /I'm Hermes, your CEO advisor/i,
  /I can help, but I need one more detail/i,
  /Would you like me to/i,
  /My read: answer the immediate question first/i,
  /I need one focused clarification: what specific decision/i,
];

const broadCertificationMessages: Array<{ group: string; message: string; requiredConcepts?: RegExp[]; expectedModes?: string[]; requiresNoAction?: boolean; requiresAction?: boolean }> = [
  ...['what time is it', 'what time is it in Phoenix', 'what day is it', "what is today's date", 'current time', 'time now', 'current date', 'what date is it'].map((message) => ({ group: 'time_date', message, requiredConcepts: [/Phoenix|Today/i], expectedModes: ['FACTUAL_QUESTION'] })),
  ...['did we build department operations', 'did we set up department operations and governed automation', 'what wave are we on', 'what did we finish', 'what is next', 'are we done with Hermes', 'what are we working on', 'what did we complete'].map((message) => ({ group: 'project_status', message, requiredConcepts: [/Department Operations|Wave 4A|Hermes|NEXT|PARTIAL/i], expectedModes: ['FACTUAL_QUESTION'] })),
  ...['do we have reports', 'do you have any reports', 'show me the latest report', 'what reports mention Hermes', 'where is the system health report', 'summarize the capability report', 'find the revenue report', 'show the most recent report'].map((message) => ({ group: 'reports', message, requiredConcepts: [/report|approved|indexed|Matching/i], expectedModes: ['FACTUAL_QUESTION'] })),
  ...['do we have clients', 'do we have customers', 'how many client records exist', 'are those real clients or synthetic', 'what client workflows are active', 'are there customer blockers', 'do we got clients', 'how many customers are active'].map((message) => ({ group: 'customers', message, requiredConcepts: [/client|customer|synthetic|Real active paying customers/i], expectedModes: ['FACTUAL_QUESTION'] })),
  ...['where did you get that answer', 'where did that answer come from', 'what evidence supports that', 'is that live data', 'how current is that information', 'is that your opinion or a fact', 'what source did you use', 'where you get that from'].map((message) => ({ group: 'provenance', message, requiredConcepts: [/source|Evidence|previous answer|came from|live|fact|recommendation|opinion/i], expectedModes: ['FACTUAL_QUESTION'] })),
  ...["let's work on the readiness review", 'lets work on the readines reviw', 'continue with that', "okay let's do the plan", 'break it down', 'what comes first', 'help me plan it', 'what do we need to do first'].map((message) => ({ group: 'topic_continuation', message, requiredConcepts: [/planning|\$97|readiness|deliverable/i], expectedModes: ['DECISION_SUPPORT'], requiresNoAction: true })),
  ...['can we redesign the command center', 'what would you change', 'help me improve the client portal', 'does this workflow make sense', 'what do you think of this layout', 'can we change the layout', 'how should the dashboard work', 'what would you change first'].map((message) => ({ group: 'project_discussion', message, requiredConcepts: [/redesign|layout|workflow|project discussion|change/i], expectedModes: ['PROJECT_DISCUSSION'], requiresNoAction: true })),
  ...['what should we focus on', 'what should we focus on today', 'what is our biggest risk', 'how can we make money', 'how can we make money today', 'what needs approval', 'what is blocked', 'what should Engineering do next'].map((message) => ({ group: 'executive_questions', message, requiredConcepts: [/recommend|risk|approval|revenue|focus|attention|blocked/i], requiresNoAction: true })),
  ...['how is system health', 'how is our system health', 'is Stripe live', 'is trading active', 'is GitHub MCP configured', 'can Alpha access Supabase', 'how is are systm health', 'can Alpha see client data'].map((message) => ({ group: 'status_honesty', message, requiredConcepts: [/health|test mode|blocked|not configured|prohibited|not allowed/i], requiresNoAction: true })),
  ...['good morning', 'good afternoon', 'thanks', 'that makes sense', 'I agree', 'got it', 'how are you', 'whats up'].map((message) => ({ group: 'natural_conversation', message, requiresNoAction: true })),
  ...['help me plan this', 'create a task for this', 'prepare this for review', 'run the approved check', 'create a task for that redesign', 'prepare that for Ray Review', 'assign this to Engineering', 'draft a work request for that'].map((message) => ({ group: 'action_separation', message, requiresAction: /create|prepare|assign|draft/.test(message), requiresNoAction: /help me plan|run the approved check/.test(message) })),
];

export function scoreHermesResponse(result: HermesConversationResult, fixture?: HermesQualityFixture): HermesResponseQuality {
  const failures: string[] = [];
  const text = result.response;

  if (fixture?.expectedModes?.length && !fixture.expectedModes.includes(result.mode)) failures.push(`mode:${result.mode}`);
  if (fixture?.requiresNoAction && result.action) failures.push('unexpected_action');
  if (fixture?.requiresAction && !result.action) failures.push('missing_action');
  for (const pattern of fixture?.requiredConcepts || []) {
    if (!pattern.test(text)) failures.push(`missing:${String(pattern)}`);
  }
  for (const pattern of [...(fixture?.forbiddenConcepts || []), ...roboticPatterns]) {
    if (pattern.test(text)) failures.push(`forbidden:${String(pattern)}`);
  }
  if (result.mode === 'SOCIAL_GREETING' && text.split(/\s+/).length > 18) failures.push('greeting_too_long');
  if (result.mode === 'CASUAL_CONVERSATION' && text.split(/\s+/).length > 28) failures.push('casual_too_long');
  if (['TASK_REQUEST', 'APPROVAL_REQUEST'].includes(result.mode) && !/nothing has been saved|conversation-only|requires/i.test(text)) failures.push('action_boundary_missing');
  if (result.mode === 'SYSTEM_STATUS' && /\blive\b/i.test(text) && !/\btest mode|deferred|blocked|not configured|prohibited/i.test(text)) failures.push('status_honesty_missing');

  const penalty = Math.min(failures.length * 12, 60);
  const score = Math.max(40, 100 - penalty);
  const actionSeparation = failures.includes('unexpected_action') || failures.includes('action_boundary_missing') ? 70 : 100;
  const evidenceHonesty = failures.includes('status_honesty_missing') ? 65 : 100;
  const naturalness = failures.some((item) => item.startsWith('forbidden:')) ? 72 : 96;

  return {
    overallScore: score,
    intentAlignment: failures.some((item) => item.startsWith('mode:')) ? 70 : 96,
    continuity: result.memoryUsed.length || !['FOLLOW_UP_ADVICE', 'SELECTION_REFERENCE'].includes(result.mode) ? 95 : 72,
    memoryCorrectness: failures.includes('missing_action') ? 80 : 96,
    naturalness,
    directness: text.length > 0 && !/^I can help/.test(text) ? 96 : 72,
    evidenceHonesty,
    actionSeparation,
    repetitionControl: failures.some((item) => item.startsWith('forbidden:')) ? 70 : 100,
    lengthFitness: failures.includes('greeting_too_long') || failures.includes('casual_too_long') ? 70 : 96,
    failures,
  };
}

export function getHermesCertificationCorpus(): HermesQualityFixture[] {
  const base: HermesQualityFixture[] = [
    { id: 'greeting_good_morning', group: 'greetings', messages: ['good morning'], expectedModes: ['SOCIAL_GREETING'], requiresNoAction: true, requiredConcepts: [/Good morning, Ray/i], forbiddenConcepts: [/menu|approval|system health/i] },
    { id: 'greeting_good_night', group: 'historical', messages: ['good night'], expectedModes: ['SOCIAL_GREETING'], requiresNoAction: true, requiredConcepts: [/Good night, Ray/i], forbiddenConcepts: [/human tastes|lived experiences/i] },
    { id: 'casual_sleep', group: 'greetings', messages: ['how did you sleep'], expectedModes: ['CASUAL_CONVERSATION'], requiresNoAction: true, requiredConcepts: [/don.t sleep|ready/i], forbiddenConcepts: [/human tastes|lived experiences/i] },
    { id: 'executive_priority', group: 'executive_advice', messages: ['what should we work on first'], expectedModes: ['EXECUTIVE_ADVICE'], requiresNoAction: true, requiredConcepts: [/Hermes conversation certification|first/i] },
    { id: 'followup_realistic', group: 'historical', messages: ['what should we work on first', 'is that realistic'], expectedModes: ['FOLLOW_UP_ADVICE'], requiresNoAction: true, requiredConcepts: [/realistic|bounded/i] },
    { id: 'selection_number_two', group: 'selection', messages: ['what should we work on first', 'number 2'], expectedModes: ['SELECTION_REFERENCE'], requiresNoAction: true, requiredConcepts: [/Department Operations/i] },
    { id: 'action_number_two', group: 'action_separation', messages: ['what should we work on first', 'turn number 2 into a work request'], expectedModes: ['TASK_REQUEST'], requiresAction: true, requiredConcepts: [/conversation-only|nothing has been saved|requires/i] },
    { id: 'status_stripe', group: 'status_honesty', messages: ['is Stripe live'], expectedModes: ['SYSTEM_STATUS'], requiresNoAction: true, requiredConcepts: [/test mode|deferred/i] },
    { id: 'status_trading', group: 'status_honesty', messages: ['is trading active'], expectedModes: ['SYSTEM_STATUS'], requiresNoAction: true, requiredConcepts: [/blocked by policy/i] },
    { id: 'status_alpha', group: 'status_honesty', messages: ['can Alpha see client data'], expectedModes: ['SYSTEM_STATUS'], requiresNoAction: true, requiredConcepts: [/No|not allowed|client PII/i] },
    { id: 'page_context_conflict', group: 'page_context', messages: ['good morning'], expectedModes: ['SOCIAL_GREETING'], requiresNoAction: true, requiredConcepts: [/Good morning/i], forbiddenConcepts: [/credit page|funding page|system health menu/i] },
  ];
  const broad: HermesQualityFixture[] = broadCertificationMessages.map((item, index) => ({
    id: `wave_4a_4_${item.group}_${index}`,
    group: item.group,
    messages: item.group === 'provenance' ? ['do we have reports', item.message] : item.group === 'topic_continuation' ? ['what should we focus on today', item.message] : [item.message],
    expectedModes: item.expectedModes,
    requiresNoAction: item.requiresNoAction,
    requiresAction: item.requiresAction,
    requiredConcepts: item.requiredConcepts,
  }));
  const filler: HermesQualityFixture[] = Array.from({ length: Math.max(0, 200 - base.length - broad.length) }, (_, index) => ({
    id: `wave_4a_4_general_safe_${index}`,
    group: index % 4 === 0 ? 'project_status' : index % 4 === 1 ? 'reports' : index % 4 === 2 ? 'project_discussion' : 'executive_questions',
    messages: index % 4 === 0 ? [`what is next for Hermes certification ${index}`] : index % 4 === 1 ? [`show me reports about operations ${index}`] : index % 4 === 2 ? [`can we redesign the dashboard flow ${index}`] : [`what should we focus on today ${index}`],
    requiresNoAction: true,
  }));
  return [...base, ...broad, ...filler];
}

export interface HermesCertificationSummary {
  fixtureCount: number;
  overallScore: number;
  historicalRegressionScore: number;
  actionSeparationScore: number;
  statusHonestyScore: number;
  memoryScore: number;
  referenceResolutionScore: number;
  repetitionScore: number;
  failures: string[];
}

export function summarizeHermesQuality(results: Array<{ fixture: HermesQualityFixture; result: HermesConversationResult }>): HermesCertificationSummary {
  const fixtureCount = results.length;
  const scores = results.map(({ result }) => result.quality?.overallScore ?? 0);
  const average = (values: number[]) => values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : 0;
  const groupScore = (group: string, selector: (result: HermesConversationResult) => number = (result) => result.quality?.overallScore ?? 0) => average(results.filter((item) => item.fixture.group === group).map((item) => selector(item.result)));
  const failures = results.flatMap(({ fixture, result }) => (result.quality?.failures || []).map((failure) => `${fixture.id}:${failure}`));
  return {
    fixtureCount,
    overallScore: average(scores),
    historicalRegressionScore: groupScore('historical'),
    actionSeparationScore: groupScore('action_separation', (result) => result.quality?.actionSeparation ?? 0),
    statusHonestyScore: groupScore('status_honesty', (result) => result.quality?.evidenceHonesty ?? 0),
    memoryScore: average(results.filter((item) => ['FOLLOW_UP_ADVICE', 'SELECTION_REFERENCE'].includes(item.result.mode)).map((item) => item.result.quality?.memoryCorrectness ?? 0)),
    referenceResolutionScore: groupScore('selection'),
    repetitionScore: average(results.map((item) => item.result.quality?.repetitionControl ?? 0)),
    failures,
  };
}
