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
  scopeKey: string;
  sourceProvenance: string[];
  confidence: 'high' | 'medium' | 'low';
}

let activeScope = 'default:default';
const stateByScope = new Map<string, AdvisoryContinuityState | null>();

const ADVISORY_FOLLOW_UP = /\b(do you think (?:it|that|this) (?:is possible|will work)|is (?:that|this|it) (?:possible|realistic|worth it)|is that a good business|can (?:we|this) (?:do it|work)|can this be a business|how hard would that be|what would it take|what (?:is|are) the risks?|what should we do first|how likely is that|what would stop us|what makes that work|should we try it|should we do it|what is the upside|what is the downside|how (?:would|can|do) we (?:test|start)(?: it)?|what is step one|how can i test this for free|what is the cheapest way to test|should we make a ray review card|is it worth pursuing)\b/i;

export function isAdvisoryFollowUpQuestion(message: string): boolean { return ADVISORY_FOLLOW_UP.test(message); }
export function setAdvisoryMemoryScope(scopeKey: string): void { activeScope = scopeKey || 'default:default'; }
export function getAdvisoryContinuity(): AdvisoryContinuityState | null {
  const state = stateByScope.get(activeScope) || null;
  return state && state.turnCount <= state.expiresAfterTurns ? { ...state } : null;
}
export function setAdvisoryContinuity(value: Omit<AdvisoryContinuityState, 'createdAt' | 'turnCount' | 'expiresAfterTurns' | 'scopeKey' | 'sourceProvenance' | 'confidence'> & { expiresAfterTurns?: number; sourceProvenance?: string[]; confidence?: 'high' | 'medium' | 'low' }): void {
  stateByScope.set(activeScope, { ...value, createdAt: new Date().toISOString(), turnCount: 0, expiresAfterTurns: value.expiresAfterTurns ?? 6, scopeKey: activeScope, sourceProvenance: value.sourceProvenance || [], confidence: value.confidence || 'medium' });
}
export function advanceAdvisoryContinuityTurn(): void {
  let state = stateByScope.get(activeScope) || null;
  if (!state) return;
  state.turnCount += 1;
  if (state.turnCount > state.expiresAfterTurns) state = null;
  stateByScope.set(activeScope, state);
}
export function clearAdvisoryContinuity(): void { stateByScope.delete(activeScope); }
export function resetAdvisoryContinuity(): void { stateByScope.delete(activeScope); }

export function answerAdvisoryFollowUp(message: string, advisory: AdvisoryContinuityState): string {
  const evidence = `\n\n**Source:** prior advisory context (${advisory.sourceProvenance.join(', ') || 'local reasoning'}). **Confidence:** ${advisory.confidence}. **Next safe action:** validate the smallest assumption before any external execution.`;
  const monthlyReadiness = /monthly readiness subscription/i.test(advisory.lastAdvisoryTopic + ' ' + advisory.lastAdvisorySummary);
  if (/what would stop us|what (?:is|are) the risks?|downside/i.test(message)) return `The main blockers are ${advisory.lastAdvisoryRisks.join(', ')}. The plan is still viable, but those are the constraints to manage first.${evidence}`;
  if (monthlyReadiness && /how (?:do|can) we start|what is step one|what should we do first/i.test(message)) return `Start with five manual pilot clients. Define one clear monthly promise, deliver readiness monitoring and funding-prep actions by hand, track engagement and progress, then validate retention before automating or scaling.${evidence}`;
  if (/how (?:would|can|do) we (?:test|start)|test this for free|cheapest way to test|what would it take|what should we do first|what makes that work/i.test(message)) return `Use a free or low-cost validation first: ${advisory.lastAdvisoryRecommendation} Keep it manual, use a one-page explanation and no-code intake form, interview 5–10 potential customers or providers, and validate organic demand before ads, inventory, staff, or equipment.${evidence}`;
  if (/good business|can this be a business|worth pursuing/i.test(message)) return `It can be a business if the demand and partner fulfillment validate. ${advisory.lastAdvisorySummary} Start with ${advisory.lastAdvisoryRecommendation} The main risks are ${advisory.lastAdvisoryRisks.join(', ')}.`;
  if (monthlyReadiness) return `Yes, I think Monthly Readiness Subscription can work, but only if it delivers ongoing value beyond the first review. The key is a clear monthly promise: readiness monitoring, funding-prep tasks, utilization guidance, business-credit steps, and reminders. The biggest risks are ${advisory.lastAdvisoryRisks.join(', ')}. I would test it with five manual pilot clients before automating.`;
  return `Yes, I think it is possible, but the realistic path is the conservative-to-realistic case first, not the stretch case. ${advisory.lastAdvisorySummary} The biggest blockers are ${advisory.lastAdvisoryRisks.join(', ')}.${evidence}`;
}
