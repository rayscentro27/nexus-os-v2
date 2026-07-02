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

const ADVISORY_FOLLOW_UP = /\b(do you think (?:it|that|this) is possible|is (?:that|this|it) (?:possible|realistic|worth it)|is that a good business|can (?:we|this) (?:do it|work)|can this be a business|how hard would that be|what would it take|what (?:is|are) the risks?|what should we do first|how likely is that|what would stop us|what makes that work|should we try it|what is the upside|what is the downside|how (?:would|can) we test it|how can i test this for free|what is the cheapest way to test|should we make a ray review card|is it worth pursuing)\b/i;

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
  if (/how (?:would|can) we test|test this for free|cheapest way to test|what would it take|what should we do first|what makes that work/i.test(message)) return `Use a free or low-cost validation first: ${advisory.lastAdvisoryRecommendation} Keep it manual, use a one-page explanation and no-code intake form, interview 5–10 potential customers or providers, and validate organic demand before ads, inventory, staff, or equipment.`;
  if (/good business|can this be a business|worth pursuing/i.test(message)) return `It can be a business if the demand and partner fulfillment validate. ${advisory.lastAdvisorySummary} Start with ${advisory.lastAdvisoryRecommendation} The main risks are ${advisory.lastAdvisoryRisks.join(', ')}.`;
  return `Yes, I think it is possible, but the realistic path is the conservative-to-realistic case first, not the stretch case. ${advisory.lastAdvisorySummary} The biggest blockers are ${advisory.lastAdvisoryRisks.join(', ')}.`;
}
