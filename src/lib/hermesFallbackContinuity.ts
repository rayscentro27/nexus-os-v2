export interface FallbackContinuityState {
  originalMessage: string;
  fallbackType: 'general_ambiguity';
  offeredOptions: string[];
  createdAt: string;
  turnCount: number;
  expiresAfterTurns: number;
}

let state: FallbackContinuityState | null = null;
const OPTION = /^(?:general recommendation|nexus|goclear\/?apex|trading|credit\/?funding|supabase lookup|status summary|ray review draft)[.!]?$/i;

export function isFallbackOptionReply(message: string): boolean { return OPTION.test(message.trim()); }
export function getFallbackContinuity(): FallbackContinuityState | null { return state && state.turnCount <= state.expiresAfterTurns ? { ...state } : null; }
export function setFallbackContinuity(originalMessage: string): void {
  state = { originalMessage, fallbackType: 'general_ambiguity', offeredOptions: ['general recommendation', 'Nexus build plan', 'business/credit/funding angle', 'Ray Review draft'], createdAt: new Date().toISOString(), turnCount: 0, expiresAfterTurns: 4 };
}
export function advanceFallbackContinuityTurn(): void { if (state && ++state.turnCount > state.expiresAfterTurns) state = null; }
export function clearFallbackContinuity(): void { state = null; }
export function resetFallbackContinuity(): void { state = null; }
