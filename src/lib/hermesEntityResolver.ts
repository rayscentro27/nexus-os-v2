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
  source: 'selectedItem' | 'visibleItem' | 'sessionMemory' | 'ambiguous' | 'unknown';
}

/** Track the last referenced entity in session memory. */
let lastReferencedEntity: VisibleItem | null = null;

/** Update the last referenced entity (call after successful resolution). */
export function setLastReferencedEntity(item: VisibleItem | null): void {
  lastReferencedEntity = item;
}

/** Get the last referenced entity. */
export function getLastReferencedEntity(): VisibleItem | null {
  return lastReferencedEntity;
}

/** Resolve an entity reference from text and page context. */
export function resolveEntity(text: string, pageContext: PageContext | null): ResolvedEntity {
  const lower = text.toLowerCase().trim();

  // "this" or "that" or "current card" — use selected or last referenced
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

  // "the first one" or "first strategy" or "first item" etc.
  const firstMatch = lower.match(/\b(first|top)\s+(strategy|item|opportunity|offer|candidate|draft|report|client|rule|action|row|card|thing)/);
  if (firstMatch && pageContext && pageContext.visibleItems && pageContext.visibleItems.length > 0) {
    const targetType = firstMatch[2];
    const match = pageContext.visibleItems.find(i =>
      i.type.toLowerCase().includes(targetType) || targetType.includes(i.type.toLowerCase())
    ) || pageContext.visibleItems[0];
    setLastReferencedEntity(match);
    return { item: match, confidence: 'high', clarificationNeeded: false, source: 'visibleItem' };
  }

  // "the second one" etc.
  const ordinals: Record<string, number> = { second: 1, third: 2, fourth: 3, fifth: 4, sixth: 5 };
  for (const [word, idx] of Object.entries(ordinals)) {
    if (lower.includes(`the ${word}`) && pageContext?.visibleItems?.[idx]) {
      setLastReferencedEntity(pageContext.visibleItems[idx]);
      return { item: pageContext.visibleItems[idx], confidence: 'high', clarificationNeeded: false, source: 'visibleItem' };
    }
  }

  // "another" or "the other one" — if we have a last referenced, find a different one
  if (/\b(another|other|next|different)\b/.test(lower) && lastReferencedEntity) {
    const others = pageContext?.visibleItems.filter(i => i.title !== lastReferencedEntity!.title) || [];
    if (others.length === 1) {
      setLastReferencedEntity(others[0]);
      return { item: others[0], confidence: 'high', clarificationNeeded: false, source: 'visibleItem' };
    }
    if (others.length > 1) {
      return {
        item: null, confidence: 'low', clarificationNeeded: true, source: 'ambiguous',
        clarificationQuestion: `Which strategy do you want — ${others.slice(0, 3).map(i => i.title).join(', ')}?`
      };
    }
  }

  // "those offers" or "this client" — search visible items by type
  const typeMatch = lower.match(/\b(these?|those)\s+(strateg(y|ies)|offer(s)?|candidate(s)?|draft(s)?|client(s)?|report(s)?|item(s)?|row(s)?|card(s)?)\b/);
  if (typeMatch && pageContext && pageContext.visibleItems && pageContext.visibleItems.length > 0) {
    const targetType = typeMatch[2].replace(/s$/, '');
    const matches = pageContext.visibleItems.filter(i =>
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
