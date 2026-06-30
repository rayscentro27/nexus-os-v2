/**
 * Hermes Source Hint / Learning Memory — stores instructions like
 * "remember that when I ask about yesterday, summarize OpenCode results first"
 *
 * localStorage-backed. Future: Supabase adapter interface.
 */

export type MemoryType = 'source_hint' | 'preference' | 'correction' | 'definition' | 'decision' | 'recurring_instruction';

export interface SourceHint {
  id: string;
  timestamp: string;
  memoryType: MemoryType;
  instruction: string;
  triggerPhrase: string;
  source: string;
  confidence: number;
  safetyLevel: 'safe' | 'gated';
}

const HINTS_KEY = 'nexus_hermes_source_hints';
const MAX_HINTS = 100;

function safe(): Storage | null {
  try { return typeof window !== 'undefined' ? window.localStorage : null; } catch { return null; }
}

function loadHints(): SourceHint[] {
  const ls = safe();
  if (!ls) return [];
  try {
    const raw = ls.getItem(HINTS_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch { return []; }
}

function saveHints(hints: SourceHint[]): void {
  const ls = safe();
  if (!ls) return;
  try { ls.setItem(HINTS_KEY, JSON.stringify(hints.slice(-MAX_HINTS))); } catch { /* ignore */ }
}

/** Detect if a message is a "remember that..." instruction. */
export function detectLearningInstruction(text: string): { isLearning: boolean; hint?: Omit<SourceHint, 'id' | 'timestamp'> } {
  const lower = text.toLowerCase().trim();

  const learningPatterns = [
    /^(remember that|from now on|next time|when i ask|look here|use this|that means|you should|always )\b/i,
    /^(remember|note|store|save) (that|this|the following)\b/i,
  ];

  const isLearning = learningPatterns.some(p => p.test(text));
  if (!isLearning) return { isLearning: false };

  // Determine memory type
  let memoryType: MemoryType = 'source_hint';
  if (/^(from now on|next time|always|when i ask|you should)/.test(lower)) {
    memoryType = 'recurring_instruction';
  } else if (/^(that means|definition|define)/.test(lower)) {
    memoryType = 'definition';
  } else if (/^(remember that|note that)/.test(lower)) {
    memoryType = 'preference';
  }

  // Extract trigger phrase
  const triggerMatch = text.match(/(?:when i ask about|for|about|regarding)\s+(.+?)(?:,\s*|\.|$)/i);
  const triggerPhrase = triggerMatch ? triggerMatch[1].trim() : '';

  return {
    isLearning: true,
    hint: {
      memoryType,
      instruction: text,
      triggerPhrase,
      source: 'user_instruction',
      confidence: 1.0,
      safetyLevel: 'safe',
    },
  };
}

/** Store a source hint. */
export function storeHint(hint: Omit<SourceHint, 'id' | 'timestamp'>): SourceHint {
  const full: SourceHint = {
    ...hint,
    id: `hint-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    timestamp: new Date().toISOString(),
  };
  const hints = loadHints();
  hints.push(full);
  saveHints(hints);
  return full;
}

/** Find hints matching a trigger phrase. */
export function findMatchingHints(triggerPhrase: string): SourceHint[] {
  const lower = triggerPhrase.toLowerCase();
  return loadHints().filter(h => {
    const trigger = h.triggerPhrase.toLowerCase();
    return lower.includes(trigger) || trigger.includes(lower) || h.memoryType === 'recurring_instruction';
  });
}

/** Get all hints. */
export function getAllHints(): SourceHint[] {
  return loadHints();
}

/** Clear all hints. */
export function clearHints(): void {
  const ls = safe();
  if (ls) try { ls.removeItem(HINTS_KEY); } catch { /* ignore */ }
}
