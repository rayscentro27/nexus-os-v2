import type { HermesAdvisoryContext, HermesAdvisoryRecommendation, HermesSelectionContext } from './hermesConversationTypes';

export interface HermesReferenceResolution {
  item: HermesAdvisoryRecommendation | null;
  confidence: number;
  referencesResolved: string[];
  reason: string;
}

const ordinalToIndex: Record<string, number> = {
  first: 0,
  second: 1,
  third: 2,
  fourth: 3,
  fifth: 4,
  last: -1,
};

export function resolveHermesReference(message: string, advisory?: HermesAdvisoryContext, selection?: HermesSelectionContext): HermesReferenceResolution {
  if (!advisory?.recommendations.length) {
    return { item: null, confidence: 0, referencesResolved: [], reason: 'No advisory context is available.' };
  }

  const lower = message.toLowerCase();
  const numberMatch = lower.match(/\b(?:number|option|#)\s*(\d+)\b/);
  if (numberMatch) {
    const index = Number(numberMatch[1]) - 1;
    const item = advisory.recommendations[index] || null;
    return item
      ? { item, confidence: 0.95, referencesResolved: [`number ${numberMatch[1]}`, item.id], reason: 'Resolved numbered reference from advisory context.' }
      : { item: null, confidence: 0.2, referencesResolved: [`number ${numberMatch[1]}`], reason: 'Number is outside the advisory recommendation list.' };
  }

  for (const [word, indexValue] of Object.entries(ordinalToIndex)) {
    if (new RegExp(`\\b(?:the )?${word}(?: one| option| recommendation)?\\b`).test(lower)) {
      const index = indexValue === -1 ? advisory.recommendations.length - 1 : indexValue;
      const item = advisory.recommendations[index] || null;
      return item
        ? { item, confidence: 0.9, referencesResolved: [word, item.id], reason: 'Resolved ordinal reference from advisory context.' }
        : { item: null, confidence: 0.2, referencesResolved: [word], reason: 'Ordinal reference is outside the advisory recommendation list.' };
    }
  }

  const named = advisory.recommendations.find((item) => {
    const haystack = `${item.label} ${item.rationale}`.toLowerCase();
    return lower.split(/\s+/).filter((token) => token.length > 4).some((token) => haystack.includes(token));
  });
  if (named) {
    return { item: named, confidence: 0.78, referencesResolved: [named.id], reason: 'Resolved named reference from advisory labels and rationale.' };
  }

  if (/\b(that|this|it|that one|this one|the recommendation|the plan|what you just said)\b/.test(lower)) {
    const selected = selection?.selectedRecommendationId
      ? advisory.recommendations.find((item) => item.id === selection.selectedRecommendationId)
      : null;
    if (selected) {
      return { item: selected, confidence: 0.88, referencesResolved: ['selected_recommendation', selected.id], reason: 'Resolved pronoun to the most recent selected recommendation.' };
    }
    const preferred = advisory.recommendations.find((item) => item.id === advisory.preferredRecommendationId) || advisory.recommendations[0];
    return { item: preferred, confidence: 0.82, referencesResolved: ['preferred_recommendation', preferred.id], reason: 'Resolved pronoun to preferred advisory recommendation.' };
  }

  return { item: null, confidence: 0.35, referencesResolved: [], reason: 'Reference could not be resolved confidently.' };
}
