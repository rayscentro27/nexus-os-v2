import type { IntentDomain } from './hermesIntentFrame';

export type ReviewMode =
  | 'business_opportunity_review'
  | 'approval_review'
  | 'client_review'
  | 'monetization_review'
  | 'research_review'
  | 'system_health_review'
  | 'product_build_planning';

export interface SessionSource {
  type: 'supabase' | 'report' | 'static' | 'page' | 'trace';
  name?: string;
  timestamp?: string;
  verification: 'verified' | 'partial' | 'unverified';
}

export interface SessionItem {
  rank?: number;
  id?: string;
  label: string;
  domain: string;
  source: string;
  score?: number;
  summary?: string;
  evidence?: string[];
}

export interface SessionFocus {
  id?: string;
  label: string;
  domain: string;
  score?: number;
  summary?: string;
  source?: string;
}

export interface SessionRecommendation {
  label: string;
  reason: string;
  domain: string;
  source?: string;
}

export interface SessionPendingDraft {
  label: string;
  domain: string;
  action: 'draft_ray_review' | 'prepare_handoff';
  source?: string;
}

export interface SessionAdvisoryContext {
  topic: string;
  domain: string;
  recommendation?: string;
  assumptions?: string[];
  risks?: string[];
  expiresAfterTurns: number;
}

export interface NexusSessionContext {
  activeDomain?: string;
  activeMode?: ReviewMode;
  activeSource?: SessionSource;
  activeList?: SessionItem[];
  currentFocus?: SessionFocus;
  lastRecommendation?: SessionRecommendation;
  pendingDraftTarget?: SessionPendingDraft;
  lastAdvisoryContext?: SessionAdvisoryContext;
  lastTrace?: unknown;
  startedAt: string;
  updatedAt: string;
  expiresAfterTurns: number;
  turnCount: number;
  scopeKey: string;
}

const sessionStore = new Map<string, NexusSessionContext>();
const DEFAULT_EXPIRY_TURNS = 10;

function createSession(scopeKey: string, domain: string, mode: ReviewMode): NexusSessionContext {
  const now = new Date().toISOString();
  return {
    activeDomain: domain,
    activeMode: mode,
    startedAt: now,
    updatedAt: now,
    expiresAfterTurns: DEFAULT_EXPIRY_TURNS,
    turnCount: 0,
    scopeKey,
  };
}

export function getActiveSession(scopeKey: string): NexusSessionContext | null {
  const session = sessionStore.get(scopeKey);
  if (!session) return null;
  if (session.turnCount > session.expiresAfterTurns) {
    sessionStore.delete(scopeKey);
    return null;
  }
  return session;
}

export function startReviewSession(scopeKey: string, domain: string, mode: ReviewMode): NexusSessionContext {
  const session = createSession(scopeKey, domain, mode);
  sessionStore.set(scopeKey, session);
  return session;
}

export function updateSessionSource(scopeKey: string, source: SessionSource): void {
  const session = sessionStore.get(scopeKey);
  if (session) {
    session.activeSource = source;
    session.updatedAt = new Date().toISOString();
  }
}

export function updateSessionList(scopeKey: string, items: SessionItem[]): void {
  const session = sessionStore.get(scopeKey);
  if (session) {
    session.activeList = items;
    session.updatedAt = new Date().toISOString();
  }
}

export function setSessionFocus(scopeKey: string, focus: SessionFocus): void {
  const session = sessionStore.get(scopeKey);
  if (session) {
    session.currentFocus = focus;
    session.updatedAt = new Date().toISOString();
  }
}

export function setSessionRecommendation(scopeKey: string, recommendation: SessionRecommendation): void {
  const session = sessionStore.get(scopeKey);
  if (session) {
    session.lastRecommendation = recommendation;
    session.updatedAt = new Date().toISOString();
  }
}

export function setSessionPendingDraft(scopeKey: string, draft: SessionPendingDraft): void {
  const session = sessionStore.get(scopeKey);
  if (session) {
    session.pendingDraftTarget = draft;
    session.updatedAt = new Date().toISOString();
  }
}

export function setSessionAdvisoryContext(scopeKey: string, advisory: SessionAdvisoryContext): void {
  const session = sessionStore.get(scopeKey);
  if (session) {
    session.lastAdvisoryContext = advisory;
    session.updatedAt = new Date().toISOString();
  }
}

export function advanceSessionTurn(scopeKey: string): void {
  const session = sessionStore.get(scopeKey);
  if (session) {
    session.turnCount++;
    session.updatedAt = new Date().toISOString();
  }
}

export function clearSession(scopeKey: string): void {
  sessionStore.delete(scopeKey);
}

export function resolveTargetFromSession(scopeKey: string, targetHint?: { type?: string; rank?: number; label?: string }): SessionFocus | null {
  const session = sessionStore.get(scopeKey);
  if (!session) return null;

  if (targetHint?.label) {
    const namedMatch = session.activeList?.find(item =>
      item.label.toLowerCase().includes(targetHint.label!.toLowerCase())
    );
    if (namedMatch) return { id: namedMatch.id, label: namedMatch.label, domain: namedMatch.domain, score: namedMatch.score, summary: namedMatch.summary, source: namedMatch.source };
  }

  if (targetHint?.rank && session.activeList) {
    const rankedItem = session.activeList.find(item => item.rank === targetHint.rank);
    if (rankedItem) return { id: rankedItem.id, label: rankedItem.label, domain: rankedItem.domain, score: rankedItem.score, summary: rankedItem.summary, source: rankedItem.source };
  }

  if (session.currentFocus) return session.currentFocus;

  if (session.activeList && session.activeList.length > 0) {
    const topItem = session.activeList.reduce((best, item) => {
      if (!best || (item.score ?? 0) > (best.score ?? 0)) return item;
      return best;
    }, session.activeList[0]);
    return { id: topItem.id, label: topItem.label, domain: topItem.domain, score: topItem.score, summary: topItem.summary, source: topItem.source };
  }

  return null;
}

export function clearExpiredSessions(): void {
  for (const [key, session] of sessionStore.entries()) {
    if (session.turnCount > session.expiresAfterTurns) {
      sessionStore.delete(key);
    }
  }
}
