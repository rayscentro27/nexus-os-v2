import type { ConversationItem } from './hermesConversationState';

export interface LastTurnTraceMemory {
  routeLevel: number; routeName: string; domain: string; usedSupabase: boolean;
  usedStaticFallback: boolean; usedModel: boolean; modelName: string | null;
  usedMemory: boolean; sources: string[]; costEstimate: string | null;
  decisionReason: string; blockedBySafety: boolean;
}
export interface SelectionMemory {
  lastList: ConversationItem[]; lastRankedList: ConversationItem[];
  lastRecommendation: ConversationItem | null; lastSelectedItem: ConversationItem | null;
  activeDomain: string | null; expiresAfterTurns: number; createdAt: string; lastUsedAt: string | null;
  scopeKey: string; provenance: string[]; turnCount: number;
}
export interface LongTermBusinessContext {
  goals: string[]; constraints: string[]; currentOffers: string[];
  activeProjects: string[]; knownBusinessModel: string; latestSectionSummary: string;
}

let activeScope = 'default:default';
const traceByScope = new Map<string, LastTurnTraceMemory | null>();
const selectionByScope = new Map<string, SelectionMemory>();
let longTermBusinessContext: LongTermBusinessContext = {
  goals: ['Generate near-term revenue', 'Grow GoClear/Apex safely'],
  constraints: ['No external sends, charges, publishing, disputes, or live trades without approval'],
  currentOffers: ['$97 Credit & Funding Readiness Review', '$297 Credit Assistant Plan', 'Monthly Readiness Subscription'],
  activeProjects: ['GoClear', 'Apex'], knownBusinessModel: 'Readiness review entry offer with assistant-plan and recurring-readiness upsells',
  latestSectionSummary: 'Revenue workflow exists; external execution remains approval-gated.',
};

function emptySelection(): SelectionMemory {
  return { lastList: [], lastRankedList: [], lastRecommendation: null, lastSelectedItem: null, activeDomain: null, expiresAfterTurns: 8, createdAt: new Date().toISOString(), lastUsedAt: null, scopeKey: activeScope, provenance: [], turnCount: 0 };
}
export function setHermesMemoryScope(scopeKey: string): void { activeScope = scopeKey || 'default:default'; }
export function getHermesMemoryScope(): string { return activeScope; }
export function getLastTurnTraceMemory(): LastTurnTraceMemory | null { return traceByScope.get(activeScope) || null; }
export function setLastTurnTraceMemory(value: LastTurnTraceMemory): void { traceByScope.set(activeScope, value); }
export function getSelectionMemory(): SelectionMemory {
  const value = selectionByScope.get(activeScope) || emptySelection();
  if (value.turnCount > value.expiresAfterTurns) { const expired = emptySelection(); selectionByScope.set(activeScope, expired); return expired; }
  return value;
}
export function updateSelectionMemory(update: Partial<SelectionMemory>): void { selectionByScope.set(activeScope, { ...getSelectionMemory(), ...update, scopeKey: activeScope }); }
export function touchSelectionMemory(): void { updateSelectionMemory({ lastUsedAt: new Date().toISOString(), turnCount: 0 }); }
export function advanceSelectionMemoryTurn(): void { const value = getSelectionMemory(); if (value.lastList.length || value.lastSelectedItem) updateSelectionMemory({ turnCount: value.turnCount + 1 }); }
export function getLongTermBusinessContext(): LongTermBusinessContext { return longTermBusinessContext; }
export function updateLongTermBusinessContext(update: Partial<LongTermBusinessContext>): void { longTermBusinessContext = { ...longTermBusinessContext, ...update }; }
export function resetHermesMemoryStores(): void { traceByScope.delete(activeScope); selectionByScope.delete(activeScope); }
