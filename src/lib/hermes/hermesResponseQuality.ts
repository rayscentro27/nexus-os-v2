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
  return [
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
