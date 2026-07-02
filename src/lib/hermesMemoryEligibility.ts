import type { RouteDecision } from './hermesRouteDecision';
import type { LastTurnTraceMemory, SelectionMemory } from './hermesMemoryStores';

export interface MemoryEligibilityInput {
  message: string; routeDecision: RouteDecision; detectedDomain: string;
  previousSelectionMemory: SelectionMemory; previousTraceMemory: LastTurnTraceMemory | null;
}
export interface MemoryEligibilityResult { eligible: boolean; traceAllowed: boolean; selectionAllowed: boolean; longTermAllowed: boolean; reason: string; matchedItem?: string; }

const FOLLOW_UP = /\b(that(?: one)?|this(?: one)?|it|those|number\s*\d+|option\s*\d+|the\s+(?:first|second|third)|pick one|create (?:a )?(?:ray review )?card for that|how do (?:we|i) implement it|continue|go deeper)\b/i;

export function evaluateMemoryEligibility(input: MemoryEligibilityInput): MemoryEligibilityResult {
  const { routeDecision: decision, previousSelectionMemory: selection } = input;
  if (decision.memoryPolicy === 'none') return { eligible: false, traceAllowed: false, selectionAllowed: false, longTermAllowed: false, reason: 'RouteDecision forbids memory.' };
  if (decision.memoryPolicy === 'last_trace_only') return { eligible: Boolean(input.previousTraceMemory), traceAllowed: true, selectionAllowed: false, longTermAllowed: false, reason: 'Only the last trace is allowed.' };
  const normalized = input.message.toLowerCase().replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ');
  const items = [selection.lastSelectedItem, selection.lastRecommendation, ...selection.lastRankedList, ...selection.lastList].filter((item): item is NonNullable<typeof item> => Boolean(item));
  const named = items.find(item => normalized.includes(item.title.toLowerCase().replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ').replace(/^\d+\s+/, '')));
  const marker = FOLLOW_UP.test(input.message);
  const selectionAllowed = decision.memoryPolicy === 'selection_only' || decision.memoryPolicy === 'selection_and_long_term';
  const longTermAllowed = decision.memoryPolicy === 'long_term_allowed' || decision.memoryPolicy === 'selection_and_long_term';
  if (selectionAllowed && (named || (marker && items.length > 0))) return { eligible: true, traceAllowed: false, selectionAllowed: true, longTermAllowed, reason: named ? 'Named selection item matched.' : 'Explicit selection follow-up marker matched an available list.', matchedItem: named?.title };
  if (longTermAllowed) return { eligible: true, traceAllowed: false, selectionAllowed: false, longTermAllowed: true, reason: 'Long-term business context is allowed; stale selection is excluded.' };
  return { eligible: false, traceAllowed: false, selectionAllowed: false, longTermAllowed: false, reason: 'Selection policy requires a follow-up marker or named item.' };
}
export function isMemoryEligible(input: MemoryEligibilityInput): boolean { return evaluateMemoryEligibility(input).eligible; }
