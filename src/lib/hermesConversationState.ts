/**
 * Hermes Conversation State — session-scoped memory for follow-up resolution.
 *
 * Tracks:
 *  - Conversation history (user + assistant messages)
 *  - Last listed items (from Supabase or static data)
 *  - Last ranked items (when Hermes ranked/sorted results)
 *  - Last recommended item
 *  - Last selected item (user clicked something)
 *  - Last Supabase query result
 *
 * Enables:
 *  - "number 3" → resolves to 3rd item in last listed set
 *  - "that one" → resolves to last referenced entity
 *  - "the first strategy" → resolves against last listed strategies
 *  - "what about the credit one" → resolves by type match
 */

export interface ConversationItem {
  id?: string;
  title: string;
  type: string;
  status?: string;
  score?: number;
  category?: string;
  revenueRange?: string;
  source?: string;
  dataSource?: string;
}

export interface ConversationState {
  history: Array<{ role: 'user' | 'assistant'; content: string; timestamp: string }>;
  lastListedItems: ConversationItem[];
  lastRankedList: ConversationItem[];
  lastRecommendedItem: ConversationItem | null;
  lastSelectedItem: ConversationItem | null;
  lastSupabaseQueryResult: {
    table: string;
    rows: unknown[];
    query: string;
    timestamp: string;
  } | null;
  lastReferencedItem: ConversationItem | null;
  lastIntent: string | null;
  lastTopic: string | null;
  lastPage: string | null;
  lastActionPlan: string | null;
  lastQuestion: string | null;
  lastAnswerSummary: string | null;
}

// Module-level session state
let conversationState: ConversationState = {
  history: [],
  lastListedItems: [],
  lastRankedList: [],
  lastRecommendedItem: null,
  lastSelectedItem: null,
  lastSupabaseQueryResult: null,
  lastReferencedItem: null,
  lastIntent: null, lastTopic: null, lastPage: null, lastActionPlan: null, lastQuestion: null, lastAnswerSummary: null,
};

/** Reset conversation state (e.g., on page reload). */
export function resetConversationState(): void {
  conversationState = {
    history: [],
    lastListedItems: [],
    lastRankedList: [],
    lastRecommendedItem: null,
    lastSelectedItem: null,
    lastSupabaseQueryResult: null,
    lastReferencedItem: null,
    lastIntent: null, lastTopic: null, lastPage: null, lastActionPlan: null, lastQuestion: null, lastAnswerSummary: null,
  };
}

/** Add a user message to history. */
export function addConversationMessage(role: 'user' | 'assistant', content: string): void {
  conversationState.history.push({ role, content, timestamp: new Date().toISOString() });
  // Keep last 50 messages
  if (conversationState.history.length > 50) {
    conversationState.history = conversationState.history.slice(-50);
  }
  if (role === 'user') conversationState.lastQuestion = content;
  else conversationState.lastAnswerSummary = content.slice(0, 500);
}

export function updateConversationContext(update: Partial<Pick<ConversationState, 'lastIntent' | 'lastTopic' | 'lastPage' | 'lastActionPlan'>>): void {
  conversationState = { ...conversationState, ...update };
}

/** Get conversation history. */
export function getConversationHistory(): ConversationState['history'] {
  return conversationState.history;
}

/** Store the last listed items (e.g., from a Supabase query or section listing). */
export function setLastListedItems(items: ConversationItem[]): void {
  conversationState.lastListedItems = items;
  // Also clear stale rank/recommend when new list arrives
  conversationState.lastRankedList = items;
}

/** Get the last listed items. */
export function getLastListedItems(): ConversationItem[] {
  return conversationState.lastListedItems;
}

/** Store a ranked list (when Hermes sorted/recommended). */
export function setLastRankedList(items: ConversationItem[]): void {
  conversationState.lastRankedList = items;
}

/** Get the ranked list. */
export function getLastRankedList(): ConversationItem[] {
  return conversationState.lastRankedList;
}

/** Set the last recommended item. */
export function setLastRecommendedItem(item: ConversationItem): void {
  conversationState.lastRecommendedItem = item;
}

/** Set the last selected item (user clicked something). */
export function setLastSelectedItem(item: ConversationItem): void {
  conversationState.lastSelectedItem = item;
  conversationState.lastReferencedItem = item;
}

/** Set the last referenced item (resolved from "this", "that", "number 3"). */
export function setLastReferencedItem(item: ConversationItem): void {
  conversationState.lastReferencedItem = item;
}

/** Get the last referenced item. */
export function getLastReferencedItem(): ConversationItem | null {
  return conversationState.lastReferencedItem;
}

/** Store Supabase query result for follow-up questions. */
export function setLastSupabaseQueryResult(
  table: string,
  rows: unknown[],
  query: string
): void {
  conversationState.lastSupabaseQueryResult = { table, rows, query, timestamp: new Date().toISOString() };
}

/** Get the last Supabase query result. */
export function getLastSupabaseQueryResult(): ConversationState['lastSupabaseQueryResult'] {
  return conversationState.lastSupabaseQueryResult;
}

/**
 * Resolve a follow-up reference like "number 3", "that one", "the first strategy".
 *
 * Returns the resolved item or null if unresolvable.
 */
export function resolveFollowUp(message: string): ConversationItem | null {
  const lower = message.toLowerCase().trim();
  const allItems = conversationState.lastRankedList.length ? conversationState.lastRankedList : conversationState.lastListedItems;

  // Named entity references are semantic memory matches, not generic pronouns.
  const normalized = lower.replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  const named = allItems.find(item => {
    const title = item.title.toLowerCase().replace(/[$]/g, '').replace(/[^a-z0-9]+/g, ' ').replace(/^\d+\s+/, '').trim();
    return title.length >= 5 && normalized.includes(title);
  });
  if (named) { conversationState.lastReferencedItem = named; return named; }

  // "number 3" / "#3" / "option 2"
  const numberMatch = lower.match(/(?:^|\b)(?:number|#|option)\s*(\d+)\b/);
  if (numberMatch) {
    const idx = parseInt(numberMatch[1], 10) - 1;
    const items = conversationState.lastRankedList.length > 0
      ? conversationState.lastRankedList
      : conversationState.lastListedItems;
    if (idx >= 0 && idx < items.length) {
      conversationState.lastReferencedItem = items[idx];
      return items[idx];
    }
    return null;
  }

  // "that one" / "that one" / "this"
  if (/\b(?:that|this|it|the\s+one)\b/i.test(lower)) {
    return conversationState.lastReferencedItem || conversationState.lastSelectedItem || conversationState.lastRecommendedItem;
  }

  // "the first one" / "first strategy" / "top item"
  const firstMatch = lower.match(/\b(first|top|second|third|fourth|fifth|last|next)\b/);
  if (firstMatch) {
    const items = conversationState.lastRankedList.length > 0
      ? conversationState.lastRankedList
      : conversationState.lastListedItems;
    if (items.length === 0) return null;

    const ordinalMap: Record<string, number> = {
      first: 0, top: 0, second: 1, third: 2, fourth: 3, fifth: 4,
      last: items.length - 1, next: Math.min(1, items.length - 1),
    };
    const idx = ordinalMap[firstMatch[1]];
    if (idx !== undefined && idx < items.length) {
      conversationState.lastReferencedItem = items[idx];
      return items[idx];
    }
    return null;
  }

  // "the credit one" / "the trading one" — match by type/category
  const typeMatch = lower.match(/\b(credit|funding|trading|research|opportunity|monetization|client|marketing|seo)\b/);
  if (typeMatch) {
    const targetType = typeMatch[1];
    const items = conversationState.lastRankedList.length ? conversationState.lastRankedList : conversationState.lastListedItems;
    const match = items.find(item =>
      item.type?.toLowerCase().includes(targetType) ||
      item.title?.toLowerCase().includes(targetType) ||
      item.category?.toLowerCase().includes(targetType)
    );
    if (match) {
      conversationState.lastReferencedItem = match;
      return match;
    }
  }

  return null;
}

/**
 * Check if a message is a follow-up reference (needs prior context).
 */
export function isFollowUpReference(message: string): boolean {
  const lower = message.toLowerCase().trim();
  // Very short messages that could reference prior context
  if (/\b(?:number|#|option)\s*\d+\b/.test(lower)) return true;
  if (/^(?:that|this|it|the\s+one|another|other|next)\b/i.test(lower)) return true;
  if (/\b(first|top|second|third|last|next)\b/.test(lower) && lower.split(' ').length <= 4) return true;
  if (/\b(which one|pick one|choose one|how do we implement|how do i implement|create (?:a )?ray review card|send that to ray review|monthly readiness subscription|do that)\b/.test(lower)) return true;
  return false;
}

export function hasConversationMemory(): boolean {
  return Boolean(conversationState.history.length || conversationState.lastListedItems.length || conversationState.lastRankedList.length || conversationState.lastReferencedItem);
}

export function getConversationState(): ConversationState { return conversationState; }
