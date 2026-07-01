/**
 * Hermes Model Cost Estimator — estimates dollar cost of model calls.
 *
 * Uses pricing config from hermesModelPricing.ts.
 * All costs are ESTIMATED — provider billing is the source of truth.
 * Never claims exact billing unless verified.
 */

import { getModelPricing } from './hermesModelPricing';

export interface CostEstimate {
  costKnown: boolean;
  estimatedInputCostUsd: number;
  estimatedOutputCostUsd: number;
  estimatedTotalCostUsd: number;
  displayCost: string;
  confidence: 'configured' | 'unknown' | 'estimated';
  note: string;
}

function roundCost(cost: number): string {
  if (cost === 0) return '$0.00';
  if (cost < 0.001) return '<$0.001';
  if (cost < 0.01) return `$${cost.toFixed(4)}`;
  return `$${cost.toFixed(4)}`;
}

/**
 * Estimate the dollar cost of a model call.
 */
export function estimateModelCallCost(params: {
  provider: string;
  model: string;
  estimatedInputTokens: number;
  estimatedOutputTokens: number;
  route: string;
}): CostEstimate {
  const { provider, model, estimatedInputTokens, estimatedOutputTokens, route } = params;

  // No-model route has zero cost
  if (route === 'no_model' || !estimatedInputTokens) {
    return {
      costKnown: true,
      estimatedInputCostUsd: 0,
      estimatedOutputCostUsd: 0,
      estimatedTotalCostUsd: 0,
      displayCost: '$0.00 (no model used)',
      confidence: 'configured',
      note: 'No model was called for this answer.',
    };
  }

  // Look up pricing
  const pricing = getModelPricing(provider, model);

  if (!pricing || pricing.pricingSource === 'unknown') {
    return {
      costKnown: false,
      estimatedInputCostUsd: 0,
      estimatedOutputCostUsd: 0,
      estimatedTotalCostUsd: 0,
      displayCost: 'pricing not configured',
      confidence: 'unknown',
      note: pricing?.notes || `No pricing configured for ${provider}/${model}. Add pricing to enable dollar estimates.`,
    };
  }

  // Local models have zero API cost
  if (provider === 'ollama') {
    return {
      costKnown: true,
      estimatedInputCostUsd: 0,
      estimatedOutputCostUsd: 0,
      estimatedTotalCostUsd: 0,
      displayCost: '$0.00 (local model)',
      confidence: 'configured',
      note: 'Local Ollama model — no API cost. Hardware electricity not estimated.',
    };
  }

  // Calculate cost from pricing table
  const inputCost = (estimatedInputTokens / 1_000_000) * (pricing.inputCostPer1MTokensUsd ?? 0);
  const outputCost = (estimatedOutputTokens / 1_000_000) * (pricing.outputCostPer1MTokensUsd ?? 0);
  const totalCost = inputCost + outputCost;

  return {
    costKnown: true,
    estimatedInputCostUsd: inputCost,
    estimatedOutputCostUsd: outputCost,
    estimatedTotalCostUsd: totalCost,
    displayCost: roundCost(totalCost),
    confidence: pricing.pricingSource === 'configured' ? 'estimated' : 'configured',
    note: `Estimated from ${pricing.pricingSource} pricing. Provider billing is source of truth. Last updated: ${pricing.lastUpdated}.`,
  };
}
