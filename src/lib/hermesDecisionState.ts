export type HermesResponseMode = 'ceo' | 'audit' | 'trace' | 'casual';

export interface LastAnswerState {
  text: string;
  route: string;
  intent: string;
  domain: string;
  sources: string[];
  usedSupabase: boolean;
  assumptions: string[];
  blockers: string[];
  confidence: 'high' | 'medium' | 'low';
  sourceStatus?: 'success' | 'partial_success' | 'empty_success' | 'failed' | 'fallback_used';
  sourceRowCount?: number;
  target?: { id?: string; label: string; type: 'record' | 'recommendation' | 'report' | 'session_item' | 'page' | 'unknown' };
  timestamp: string;
}

export interface LastSafetyDecision {
  request: string;
  reason: string;
  blockedAction: string;
  safeAlternatives: string[];
  timestamp: string;
}

export interface LastRecommendationDecision {
  label: string;
  domain: string;
  reason: string;
  source: string;
  timestamp: string;
}

export interface HermesDecisionState {
  lastAnswer: LastAnswerState | null;
  lastSafetyDecision: LastSafetyDecision | null;
  lastRecommendation: LastRecommendationDecision | null;
  responseMode: HermesResponseMode;
}

const states = new Map<string, HermesDecisionState>();
const empty = (): HermesDecisionState => ({ lastAnswer: null, lastSafetyDecision: null, lastRecommendation: null, responseMode: 'ceo' });

export function getHermesDecisionState(scopeKey: string): HermesDecisionState {
  const state = states.get(scopeKey) || empty();
  if (!states.has(scopeKey)) states.set(scopeKey, state);
  return state;
}

export function updateHermesDecisionState(scopeKey: string, update: Partial<HermesDecisionState>): void {
  states.set(scopeKey, { ...getHermesDecisionState(scopeKey), ...update });
}

export function clearHermesDecisionState(scopeKey: string): void { states.delete(scopeKey); }
