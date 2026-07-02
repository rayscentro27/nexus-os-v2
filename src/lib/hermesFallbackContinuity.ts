export interface FallbackContinuityState {
  originalMessage: string;
  fallbackType: 'general_ambiguity';
  offeredOptions: string[];
  createdAt: string;
  turnCount: number;
  expiresAfterTurns: number;
}

let activeScope = 'default:default';
const states = new Map<string, FallbackContinuityState | null>();
const current = () => states.get(activeScope) || null;
export function setFallbackMemoryScope(scopeKey: string): void { activeScope = scopeKey || 'default:default'; }
const OPTION = /^(?:general recommendation|nexus|goclear\/?apex|trading|credit\/?funding|supabase lookup|status summary|ray review draft)[.!]?$/i;

export function isFallbackOptionReply(message: string): boolean { return OPTION.test(message.trim()); }
export function getFallbackContinuity(): FallbackContinuityState | null { const state = current(); return state && state.turnCount <= state.expiresAfterTurns ? { ...state } : null; }
export function setFallbackContinuity(originalMessage: string): void {
  states.set(activeScope, { originalMessage, fallbackType: 'general_ambiguity', offeredOptions: ['general recommendation', 'Nexus build plan', 'business/credit/funding angle', 'Ray Review draft'], createdAt: new Date().toISOString(), turnCount: 0, expiresAfterTurns: 4 });
}
export function advanceFallbackContinuityTurn(): void { const state = current(); if (state && ++state.turnCount > state.expiresAfterTurns) states.delete(activeScope); else if (state) states.set(activeScope, state); }
export function clearFallbackContinuity(): void { states.delete(activeScope); }
export function resetFallbackContinuity(): void { states.delete(activeScope); }
