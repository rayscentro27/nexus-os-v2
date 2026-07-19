import type { HermesAdvisoryContext, HermesConversationInput, HermesConversationSession, HermesConversationMode, HermesConversationTrace } from './hermesConversationTypes';

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
  activeAdvisoryIdBefore?: string;
  resolvedAdvisoryId?: string;
  resolutionMethod: NonNullable<HermesConversationTrace['resolutionMethod']>;
}

const tokens = (value: string): string[] => value.toLowerCase().split(/[^a-z0-9$]+/).filter((token) => token.length > 2);

function getAdvisoryHistory(session: HermesConversationSession): HermesAdvisoryContext[] {
  const history = Array.isArray(session.advisoryHistory) ? session.advisoryHistory : [];
  const withCurrent = session.advisoryContext && !history.some((item) => item.advisoryId === session.advisoryContext?.advisoryId)
    ? [...history, session.advisoryContext]
    : history;
  return withCurrent.filter(isHermesAdvisoryContextFresh).slice(-8);
}

function getActiveAdvisory(session: HermesConversationSession): HermesAdvisoryContext | undefined {
  const history = getAdvisoryHistory(session);
  const activeId = session.activeAdvisoryId || session.advisoryContextId;
  const active = activeId ? history.find((item) => item.advisoryId === activeId) : undefined;
  if (active && isHermesAdvisoryContextFresh(active)) return active;
  const markedActive = [...history].reverse().find((item) => item.status === 'ACTIVE');
  if (markedActive) return markedActive;
  return isHermesAdvisoryContextFresh(session.advisoryContext) ? session.advisoryContext : history[history.length - 1];
}

function resolveExplicitHistoricalAdvisory(message: string, session: HermesConversationSession): HermesAdvisoryContext | undefined {
  const lower = message.toLowerCase();
  const explicitRecall = /\b(going back to|go back to|return to|what about|earlier|previous|the first priority|first priority)\b/.test(lower);
  if (!explicitRecall) return undefined;
  const messageTokens = tokens(lower);
  const scored = [...getAdvisoryHistory(session)].map((advisory) => {
    const haystack = [
      advisory.topic,
      advisory.topicId,
      advisory.topicLabel,
      advisory.summary,
      advisory.recommendation?.title,
      ...advisory.recommendations.map((item) => `${item.label} ${item.rationale}`),
    ].filter(Boolean).join(' ').toLowerCase();
    const score = messageTokens.reduce((total, token) => total + (haystack.includes(token) ? (token.length > 4 ? 2 : 1) : 0), 0);
    return { advisory, score };
  }).filter((item) => item.score > 1);
  scored.sort((a, b) => b.score - a.score);
  return scored[0]?.advisory;
}

export function resolveHermesMemory(input: HermesConversationInput, mode: HermesConversationMode): HermesMemoryResolution {
  const base = createHermesConversationSession({
    ...(input.session || {}),
    sessionId: input.session?.sessionId || input.sessionId,
    actorId: input.actorId || input.session?.actorId,
    channel: input.channel || input.session?.channel || 'unknown',
  });
  const topicChanged = shouldResetHermesTopic(input.message, base);
  const explicitAdvisory = topicChanged ? undefined : resolveExplicitHistoricalAdvisory(input.message, base);
  const activeAdvisory = topicChanged ? undefined : getActiveAdvisory(base);
  const advisoryContext = explicitAdvisory || activeAdvisory;
  const memoryUsed: string[] = [];
  const activeAdvisoryIdBefore = base.activeAdvisoryId || base.advisoryContextId || base.advisoryContext?.advisoryId;
  const resolutionMethod: NonNullable<HermesConversationTrace['resolutionMethod']> = explicitAdvisory
    ? 'EXPLICIT_TOPIC'
    : advisoryContext && ['FOLLOW_UP_ADVICE', 'SELECTION_REFERENCE', 'TASK_REQUEST', 'APPROVAL_REQUEST'].includes(mode)
      ? 'ACTIVE_ADVISORY'
      : 'NONE';

  if (advisoryContext && ['FOLLOW_UP_ADVICE', 'SELECTION_REFERENCE', 'TASK_REQUEST', 'APPROVAL_REQUEST'].includes(mode)) {
    memoryUsed.push('advisory_memory');
  }
  if (base.selectionContext && ['SELECTION_REFERENCE', 'TASK_REQUEST', 'APPROVAL_REQUEST'].includes(mode)) {
    memoryUsed.push('selection_memory');
  }
  if (base.lastUserMessage) memoryUsed.push('immediate_prior_turn');

  return {
    session: topicChanged ? { ...base, advisoryContext: undefined, selectionContext: undefined, advisoryContextId: undefined, selectionContextId: undefined, activeAdvisoryId: undefined } : base,
    memoryUsed,
    advisoryContext,
    topicChanged,
    activeAdvisoryIdBefore,
    resolvedAdvisoryId: advisoryContext?.advisoryId,
    resolutionMethod,
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
    selectedRecommendationId?: string;
  },
): HermesConversationSession {
  const activeTopic = update.advisoryContext?.topic || session.activeTopic || detectTopic(update.message);
  const recentIntentHistory = [...session.recentIntentHistory, update.intent].slice(-12);
  const recentResponseStrategies = [...session.recentResponseStrategies, update.strategy].slice(-12);
  const existingHistory = getAdvisoryHistory(session);
  const now = nowIso();
  const nextAdvisory = update.advisoryContext
    ? {
        ...update.advisoryContext,
        status: 'ACTIVE' as const,
        updatedAt: now,
        supersedesAdvisoryId: session.activeAdvisoryId || session.advisoryContextId,
      }
    : undefined;
  const advisoryHistory = nextAdvisory
    ? [
        ...existingHistory
          .filter((item) => item.advisoryId !== nextAdvisory.advisoryId)
          .map((item) => item.advisoryId === (session.activeAdvisoryId || session.advisoryContextId)
            ? { ...item, status: 'SUPERSEDED' as const, updatedAt: now }
            : item),
        nextAdvisory,
      ].slice(-8)
    : existingHistory;
  return {
    ...session,
    activeMode: update.mode,
    activeTopic,
    lastUserMessage: update.message,
    lastHermesResponse: update.response.slice(0, 1200),
    advisoryContextId: nextAdvisory?.advisoryId || session.advisoryContextId,
    activeAdvisoryId: nextAdvisory?.advisoryId || session.activeAdvisoryId,
    advisoryHistory,
    selectionContextId: nextAdvisory ? `selection-${nextAdvisory.advisoryId}` : session.selectionContextId,
    advisoryContext: nextAdvisory || session.advisoryContext,
    selectionContext: nextAdvisory ? {
      selectionContextId: `selection-${nextAdvisory.advisoryId}`,
      items: nextAdvisory.recommendations,
      selectedRecommendationId: nextAdvisory.preferredRecommendationId,
      createdAt: nextAdvisory.createdAt,
    } : update.selectedRecommendationId && session.selectionContext ? {
      ...session.selectionContext,
      selectedRecommendationId: update.selectedRecommendationId,
    } : session.selectionContext,
    recentIntentHistory,
    recentResponseStrategies,
    updatedAt: now,
  };
}
