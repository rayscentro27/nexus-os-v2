import type { HermesAdvisoryContext, HermesConversationInput, HermesConversationSession, HermesConversationMode } from './hermesConversationTypes';

const nowIso = () => new Date().toISOString();

export function createHermesConversationSession(partial: Partial<HermesConversationSession> = {}): HermesConversationSession {
  const now = nowIso();
  return {
    sessionId: partial.sessionId || `hermes-session-${now}`,
    brainId: 'hermes',
    actorId: partial.actorId,
    channel: partial.channel || 'unknown',
    recentIntentHistory: partial.recentIntentHistory || [],
    recentResponseStrategies: partial.recentResponseStrategies || [],
    startedAt: partial.startedAt || now,
    updatedAt: partial.updatedAt || now,
    ...partial,
  };
}

export function isHermesAdvisoryContextFresh(advisory?: HermesAdvisoryContext): boolean {
  if (!advisory) return false;
  if (!advisory.expiresAt) return true;
  return new Date(advisory.expiresAt).getTime() > Date.now();
}

function detectTopic(message: string): string {
  const lower = message.toLowerCase();
  if (/\b(marketing|content|campaign|creative)\b/.test(lower)) return 'marketing';
  if (/\b(client|customer|document|upload|credit|funding|readiness)\b/.test(lower)) return 'client_operations';
  if (/\b(stripe|revenue|money|sales|offer)\b/.test(lower)) return 'revenue';
  if (/\b(system|deployment|build|health|capability)\b/.test(lower)) return 'system_operations';
  if (/\b(repo|github|research|alpha)\b/.test(lower)) return 'research';
  return 'general';
}

export function shouldResetHermesTopic(message: string, session: HermesConversationSession): boolean {
  if (!session.activeTopic) return false;
  const nextTopic = detectTopic(message);
  if (nextTopic === 'general') return false;
  return session.activeTopic !== 'general' && nextTopic !== session.activeTopic && /\b(change|switch|now|new topic|discuss|move to|instead)\b/i.test(message);
}

export interface HermesMemoryResolution {
  session: HermesConversationSession;
  memoryUsed: string[];
  advisoryContext?: HermesAdvisoryContext;
  topicChanged: boolean;
}

export function resolveHermesMemory(input: HermesConversationInput, mode: HermesConversationMode): HermesMemoryResolution {
  const base = createHermesConversationSession({
    ...(input.session || {}),
    sessionId: input.session?.sessionId || input.sessionId,
    actorId: input.actorId || input.session?.actorId,
    channel: input.channel || input.session?.channel || 'unknown',
  });
  const topicChanged = shouldResetHermesTopic(input.message, base);
  const advisoryContext = topicChanged ? undefined : (isHermesAdvisoryContextFresh(base.advisoryContext) ? base.advisoryContext : undefined);
  const memoryUsed: string[] = [];

  if (advisoryContext && ['FOLLOW_UP_ADVICE', 'SELECTION_REFERENCE', 'TASK_REQUEST', 'APPROVAL_REQUEST'].includes(mode)) {
    memoryUsed.push('advisory_memory');
  }
  if (base.selectionContext && ['SELECTION_REFERENCE', 'TASK_REQUEST', 'APPROVAL_REQUEST'].includes(mode)) {
    memoryUsed.push('selection_memory');
  }
  if (base.lastUserMessage) memoryUsed.push('immediate_prior_turn');

  return {
    session: topicChanged ? { ...base, advisoryContext: undefined, selectionContext: undefined, advisoryContextId: undefined, selectionContextId: undefined } : base,
    memoryUsed,
    advisoryContext,
    topicChanged,
  };
}

export function updateHermesSessionAfterResponse(
  session: HermesConversationSession,
  update: {
    mode: HermesConversationMode;
    intent: string;
    message: string;
    response: string;
    strategy: HermesConversationSession['recentResponseStrategies'][number];
    advisoryContext?: HermesAdvisoryContext;
  },
): HermesConversationSession {
  const activeTopic = update.advisoryContext?.topic || session.activeTopic || detectTopic(update.message);
  const recentIntentHistory = [...session.recentIntentHistory, update.intent].slice(-12);
  const recentResponseStrategies = [...session.recentResponseStrategies, update.strategy].slice(-12);
  return {
    ...session,
    activeMode: update.mode,
    activeTopic,
    lastUserMessage: update.message,
    lastHermesResponse: update.response.slice(0, 1200),
    advisoryContextId: update.advisoryContext?.advisoryId || session.advisoryContextId,
    selectionContextId: update.advisoryContext ? `selection-${update.advisoryContext.advisoryId}` : session.selectionContextId,
    advisoryContext: update.advisoryContext || session.advisoryContext,
    selectionContext: update.advisoryContext ? {
      selectionContextId: `selection-${update.advisoryContext.advisoryId}`,
      items: update.advisoryContext.recommendations,
      selectedRecommendationId: update.advisoryContext.preferredRecommendationId,
      createdAt: update.advisoryContext.createdAt,
    } : session.selectionContext,
    recentIntentHistory,
    recentResponseStrategies,
    updatedAt: nowIso(),
  };
}
