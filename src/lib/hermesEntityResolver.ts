/**
 * Hermes Entity Resolver — resolves references like "this", "that", "the first one",
 * "first strategy", "this client", etc. from page context and session memory.
 */

import type { VisibleItem, PageContext } from './hermesContextBridge';

export interface ResolvedEntity {
  item: VisibleItem | null;
  confidence: 'high' | 'medium' | 'low' | 'none';
  clarificationNeeded: boolean;
  clarificationQuestion?: string;
  source: 'selectedItem' | 'visibleItem' | 'sessionMemory' | 'lastListed' | 'ambiguous' | 'unknown';
}

/** Track the last referenced entity in session memory. */
let lastReferencedEntity: VisibleItem | null = null;

/** Track the last Hermes-listed records (from live Supabase responses). */
let lastHermesListedRecords: VisibleItem[] = [];

/** Update the last referenced entity (call after successful resolution). */
export function setLastReferencedEntity(item: VisibleItem | null): void {
  lastReferencedEntity = item;
}

/** Get the last referenced entity. */
export function getLastReferencedEntity(): VisibleItem | null {
  return lastReferencedEntity;
}

/** Store the last Hermes-listed records so "the first one" resolves against them. */
export function setLastHermesListedRecords(items: VisibleItem[]): void {
  lastHermesListedRecords = items;
}

/** Get the last Hermes-listed records. */
export function getLastHermesListedRecords(): VisibleItem[] {
  return lastHermesListedRecords;
}

/** Resolve an entity reference from text and page context. */
export function resolveEntity(text: string, pageContext: PageContext | null): ResolvedEntity {
  const lower = text.toLowerCase().trim();

  // Merge visibleItems and lastHermesListedRecords for resolution
  const visibleItems = pageContext?.visibleItems || [];
  const allCandidates = [...visibleItems, ...lastHermesListedRecords.filter(
    lr => !visibleItems.some(vi => vi.title === lr.title)
  )];

  // "the first one" or "first strategy" or "review the first" etc.
  const firstMatch = lower.match(/\b(first|top)\s*(strategy|item|opportunity|offer|candidate|draft|report|client|rule|action|row|card|thing|one)?/);
  const reviewFirstMatch = lower.match(/\b(review|analyze|open|show|tell me about|look at)\s+(the\s+)?(first|top|second|third|last|next)/);
  const ordinalForReview = reviewFirstMatch ? reviewFirstMatch[3] : null;
  if ((firstMatch || ordinalForReview) && allCandidates.length > 0) {
    const targetType = firstMatch?.[2] || 'item';
    let match;
    if (ordinalForReview === 'second') match = allCandidates[1];
    else if (ordinalForReview === 'third') match = allCandidates[2];
    else if (ordinalForReview === 'last' || ordinalForReview === 'next') match = allCandidates[allCandidates.length - 1];
    else match = allCandidates.find(i => i.type.toLowerCase().includes(targetType) || targetType.includes(i.type.toLowerCase())) || allCandidates[0];
    if (match) {
      setLastReferencedEntity(match);
      return { item: match, confidence: 'high', clarificationNeeded: false, source: visibleItems.some(vi => vi.title === match.title) ? 'visibleItem' : 'lastListed' };
    }
  }

  // "this" or "that" or "current card" — use selected or last referenced.
  // Run after ordinal resolution so "first strategy on this page" resolves the first strategy.
  if (/\b(this|that|current|selected)\b/.test(lower)) {
    if (pageContext?.selectedItem) {
      setLastReferencedEntity(pageContext.selectedItem);
      return { item: pageContext.selectedItem, confidence: 'high', clarificationNeeded: false, source: 'selectedItem' };
    }
    if (lastReferencedEntity) {
      return { item: lastReferencedEntity, confidence: 'medium', clarificationNeeded: false, source: 'sessionMemory' };
    }
    return {
      item: null, confidence: 'low', clarificationNeeded: true, source: 'ambiguous',
      clarificationQuestion: 'Which item are you referring to? I don\'t have a selected item on the current page.'
    };
  }

  // "the second one" etc.
  const ordinals: Record<string, number> = { second: 1, third: 2, fourth: 3, fifth: 4, sixth: 5 };
  for (const [word, idx] of Object.entries(ordinals)) {
    if (lower.includes(`the ${word}`) && allCandidates[idx]) {
      setLastReferencedEntity(allCandidates[idx]);
      return { item: allCandidates[idx], confidence: 'high', clarificationNeeded: false, source: visibleItems.some(vi => vi.title === allCandidates[idx].title) ? 'visibleItem' : 'lastListed' };
    }
  }

  // "last one" or "last item"
  if (/\b(last|final)\b/.test(lower) && allCandidates.length > 0) {
    const last = allCandidates[allCandidates.length - 1];
    setLastReferencedEntity(last);
    return { item: last, confidence: 'high', clarificationNeeded: false, source: visibleItems.some(vi => vi.title === last.title) ? 'visibleItem' : 'lastListed' };
  }

  // "another" or "the other one" — if we have a last referenced, find a different one
  if (/\b(another|other|next|different)\b/.test(lower) && lastReferencedEntity) {
    const others = allCandidates.filter(i => i.title !== lastReferencedEntity!.title) || [];
    if (others.length === 1) {
      setLastReferencedEntity(others[0]);
      return { item: others[0], confidence: 'high', clarificationNeeded: false, source: 'visibleItem' };
    }
    if (others.length > 1) {
      return {
        item: null, confidence: 'low', clarificationNeeded: true, source: 'ambiguous',
        clarificationQuestion: `Which do you want — ${others.slice(0, 3).map(i => i.title).join(', ')}?`
      };
    }
  }

  // "those offers" or "this client" — search visible items by type
  const typeMatch = lower.match(/\b(these?|those)\s+(strateg(y|ies)|offer(s)?|candidate(s)?|draft(s)?|client(s)?|report(s)?|item(s)?|row(s)?|card(s)?)\b/);
  if (typeMatch && allCandidates.length > 0) {
    const targetType = typeMatch[2].replace(/s$/, '');
    const matches = allCandidates.filter(i =>
      i.type.toLowerCase().includes(targetType) || targetType.includes(i.type.toLowerCase())
    );
    if (matches.length === 1) {
      setLastReferencedEntity(matches[0]);
      return { item: matches[0], confidence: 'high', clarificationNeeded: false, source: 'visibleItem' };
    }
    if (matches.length > 1) {
      return {
        item: matches[0], confidence: 'medium', clarificationNeeded: false, source: 'visibleItem'
      };
    }
  }

  return { item: null, confidence: 'none', clarificationNeeded: false, source: 'unknown' };
}
