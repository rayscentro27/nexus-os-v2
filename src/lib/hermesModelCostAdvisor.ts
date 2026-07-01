/**
 * Hermes Model Cost Advisor — explains model cost in plain language
 * and recommends cost-reduction strategies.
 */

import { estimateModelCallCost, type CostEstimate } from './hermesModelCostEstimator';

export interface CostAdvice {
  summary: string;
  wasNecessary: boolean;
  cheaperAlternative: string;
  reductionTips: string[];
}

const ROUTE_LABELS: Record<string, string> = {
  no_model: 'local context (no model)',
  cheap_model: 'cheap model',
  primary_model: 'primary model',
  blocked_or_gated: 'blocked/gated',
};

/**
 * Get cost advice for a model call.
 */
export function getCostAdvice(params: {
  route: string;
  reason: string;
  provider: string;
  model: string;
  estimatedInputTokens: number;
  estimatedOutputTokens: number;
  wasModelCalled: boolean;
}): CostAdvice {
  const { route, reason, provider, model, estimatedInputTokens, estimatedOutputTokens, wasModelCalled } = params;

  const cost = estimateModelCallCost({
    provider,
    model,
    estimatedInputTokens,
    estimatedOutputTokens,
    route,
  });

  // Determine if model was necessary
  const wasNecessary = wasModelCallNecessary(route, reason);

  // Get cheaper alternative
  const cheaperAlternative = getCheaperAlternative(route);

  // Get reduction tips
  const reductionTips = getReductionTips(route, wasModelCalled);

  // Build summary
  const summary = buildCostSummary(cost, route, provider, model, estimatedInputTokens, estimatedOutputTokens, wasNecessary, cheaperAlternative);

  return { summary, wasNecessary, cheaperAlternative, reductionTips };
}

function wasModelCallNecessary(route: string, reason: string): boolean {
  if (route === 'no_model') return false;
  if (route === 'primary_model') {
    const reasons = reason.toLowerCase();
    if (reasons.includes('strategy') || reasons.includes('synthesis') || reasons.includes('complex')) return true;
    if (reasons.includes('rewrite') || reasons.includes('format') || reasons.includes('brief')) return false;
  }
  if (route === 'cheap_model') {
    const reasons = reason.toLowerCase();
    if (reasons.includes('rewrite') || reasons.includes('format') || reasons.includes('brief')) return true;
  }
  return true;
}

function getCheaperAlternative(route: string): string {
  switch (route) {
    case 'primary_model':
      return 'cheap_model or no_model for simple questions';
    case 'cheap_model':
      return 'no_model for status/Supabase count questions';
    case 'no_model':
      return 'Already cheapest route — no model used.';
    default:
      return 'no_model for simple questions';
  }
}

function getReductionTips(route: string, wasModelCalled: boolean): string[] {
  const tips: string[] = [];

  if (!wasModelCalled) {
    tips.push('No model was used — this was already free.');
    return tips;
  }

  if (route === 'primary_model') {
    tips.push('Ask for a brief answer instead of a detailed analysis.');
    tips.push('Limit sources — ask about one report instead of the full audit.');
    tips.push('Use no_model for status questions like "how many rows" or "is it running".');
    tips.push('Use cheap_model for short rewrites by saying "briefly" or "in plain English".');
  }

  if (route === 'cheap_model') {
    tips.push('This was already low-cost. To reduce further, ask for a one-line answer.');
    tips.push('For simple status questions, Hermes can answer locally without the model.');
  }

  tips.push('Keep context packets small — Hermes already does this.');
  tips.push('Background jobs default to no_model to avoid unnecessary token spend.');

  return tips;
}

function buildCostSummary(
  cost: CostEstimate,
  route: string,
  provider: string,
  model: string,
  inputTokens: number,
  outputTokens: number,
  wasNecessary: boolean,
  cheaperAlternative: string
): string {
  const routeLabel = ROUTE_LABELS[route] || route;

  if (cost.confidence === 'unknown') {
    return `Hermes used the ${routeLabel} route (${provider}/${model}). Tokens: ~${inputTokens} in, ~${outputTokens} out. Cost: ${cost.displayCost}. ${cost.note} To reduce cost, use no_model for simple status questions.`;
  }

  if (cost.estimatedTotalCostUsd === 0) {
    if (provider === 'ollama') {
      return `Hermes used the ${routeLabel} route with local Ollama (${model}). Tokens: ~${inputTokens} in, ~${outputTokens} out. Cost: $0.00 (local model, no API charges).`;
    }
    return `No model cost for that answer. Hermes used local context/router logic.`;
  }

  const necessity = wasNecessary
    ? 'This call was appropriate for the question complexity.'
    : `This call may not have been necessary. ${cheaperAlternative}.`;

  return `Hermes used the ${routeLabel} route (${provider}/${model}). Tokens: ~${inputTokens} in, ~${outputTokens} out. Estimated cost: ${cost.displayCost}. ${necessity} To reduce cost: ${cheaperAlternative}.`;
}

/**
 * Get answer to "How can we reduce token cost?"
 */
export function getCostReductionAnswer(): string {
  return `Token cost reduction strategies:

1. Use no_model for status questions — "how many rows", "is it running", "what is the source", favorite food, jokes, scheduling, memory/recall
2. Use cheap_model for short rewrites — "rewrite this", "simplify", "briefly explain", "in plain English"
3. Reserve primary_model for strategy and deep reasoning — "compare opportunities", "analyze the audit", "recommend a plan"
4. Keep context packets small — Hermes already does this automatically
5. Avoid sending full reports — Hermes packs only relevant excerpts
6. Cap output length — Hermes caps at 1200 tokens for primary, 500 for cheap
7. Background jobs default to no_model — no token spend unless explicitly allowed
8. Avoid recursive model loops — each question gets one model call max

Current pricing (estimated):
• openai/gpt-4o-mini: $0.15/1M input, $0.60/1M output
• A typical cheap_model call (~50 input, ~200 output): ~$0.0001
• A typical primary_model call (~500 input, ~1000 output): ~$0.001

Provider billing is the source of truth. These are estimates.`;
}
