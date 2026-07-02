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
}
export interface LongTermBusinessContext {
  goals: string[]; constraints: string[]; currentOffers: string[];
  activeProjects: string[]; knownBusinessModel: string; latestSectionSummary: string;
}

let lastTurnTraceMemory: LastTurnTraceMemory | null = null;
let selectionMemory: SelectionMemory = emptySelection();
let longTermBusinessContext: LongTermBusinessContext = {
  goals: ['Generate near-term revenue', 'Grow GoClear/Apex safely'],
  constraints: ['No external sends, charges, publishing, disputes, or live trades without approval'],
  currentOffers: ['$97 Credit & Funding Readiness Review', '$297 Credit Assistant Plan', 'Monthly Readiness Subscription'],
  activeProjects: ['GoClear', 'Apex'], knownBusinessModel: 'Readiness review entry offer with assistant-plan and recurring-readiness upsells',
  latestSectionSummary: 'Revenue workflow exists; external execution remains approval-gated.',
};

function emptySelection(): SelectionMemory {
  return { lastList: [], lastRankedList: [], lastRecommendation: null, lastSelectedItem: null, activeDomain: null, expiresAfterTurns: 8, createdAt: new Date().toISOString(), lastUsedAt: null };
}
export function getLastTurnTraceMemory(): LastTurnTraceMemory | null { return lastTurnTraceMemory; }
export function setLastTurnTraceMemory(value: LastTurnTraceMemory): void { lastTurnTraceMemory = value; }
export function getSelectionMemory(): SelectionMemory { return selectionMemory; }
export function updateSelectionMemory(update: Partial<SelectionMemory>): void { selectionMemory = { ...selectionMemory, ...update }; }
export function touchSelectionMemory(): void { selectionMemory.lastUsedAt = new Date().toISOString(); }
export function getLongTermBusinessContext(): LongTermBusinessContext { return longTermBusinessContext; }
export function updateLongTermBusinessContext(update: Partial<LongTermBusinessContext>): void { longTermBusinessContext = { ...longTermBusinessContext, ...update }; }
export function resetHermesMemoryStores(): void { lastTurnTraceMemory = null; selectionMemory = emptySelection(); }
