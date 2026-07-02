export interface AdvisoryContinuityState {
  lastAdvisoryTopic: string;
  lastAdvisoryDomain: string;
  lastAdvisorySummary: string;
  lastAdvisoryAssumptions: string[];
  lastAdvisoryRecommendation: string;
  lastAdvisoryRisks: string[];
  createdAt: string;
  turnCount: number;
  expiresAfterTurns: number;
}

let state: AdvisoryContinuityState | null = null;

const ADVISORY_FOLLOW_UP = /\b(do you think (?:it|that|this) is possible|is (?:that|this|it) (?:possible|realistic|worth it)|can (?:we|this) (?:do it|work)|how hard would that be|what would it take|what (?:is|are) the risks?|what should we do first|how likely is that|what would stop us|what makes that work|should we try it|what is the upside|what is the downside)\b/i;

export function isAdvisoryFollowUpQuestion(message: string): boolean { return ADVISORY_FOLLOW_UP.test(message); }
export function getAdvisoryContinuity(): AdvisoryContinuityState | null {
  return state && state.turnCount <= state.expiresAfterTurns ? { ...state } : null;
}
export function setAdvisoryContinuity(value: Omit<AdvisoryContinuityState, 'createdAt' | 'turnCount' | 'expiresAfterTurns'> & { expiresAfterTurns?: number }): void {
  state = { ...value, createdAt: new Date().toISOString(), turnCount: 0, expiresAfterTurns: value.expiresAfterTurns ?? 6 };
}
export function advanceAdvisoryContinuityTurn(): void {
  if (!state) return;
  state.turnCount += 1;
  if (state.turnCount > state.expiresAfterTurns) state = null;
}
export function clearAdvisoryContinuity(): void { state = null; }
export function resetAdvisoryContinuity(): void { state = null; }

export function answerAdvisoryFollowUp(message: string, advisory: AdvisoryContinuityState): string {
  if (/what would stop us|what (?:is|are) the risks?|downside/i.test(message)) return `The main blockers are ${advisory.lastAdvisoryRisks.join(', ')}. The plan is still viable, but those are the constraints to manage first.`;
  if (/what would it take|what should we do first|what makes that work/i.test(message)) return `It would take disciplined execution around ${advisory.lastAdvisoryAssumptions.join(', ')}. The first move is ${advisory.lastAdvisoryRecommendation}`;
  return `Yes, I think it is possible, but the realistic path is the conservative-to-realistic case first, not the stretch case. ${advisory.lastAdvisorySummary} The biggest blockers are ${advisory.lastAdvisoryRisks.join(', ')}.`;
}
