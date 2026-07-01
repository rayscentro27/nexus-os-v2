/**
 * Hermes Model Pricing Configuration — estimated cost tables.
 *
 * Pricing is estimated from public provider documentation.
 * Provider billing is the source of truth, not this config.
 * Costs are labeled as estimated unless verified against actual billing.
 */

export interface ModelPricing {
  provider: string;
  model: string;
  inputCostPer1MTokensUsd: number | null;
  outputCostPer1MTokensUsd: number | null;
  pricingSource: 'configured' | 'unknown' | 'manual';
  lastUpdated: string;
  notes: string;
}

const PRICING_TABLE: ModelPricing[] = [
  {
    provider: 'openrouter',
    model: 'openai/gpt-4o-mini',
    inputCostPer1MTokensUsd: 0.15,
    outputCostPer1MTokensUsd: 0.60,
    pricingSource: 'configured',
    lastUpdated: '2025-01-01',
    notes: 'Estimated from OpenRouter public pricing. Provider billing is source of truth.',
  },
  {
    provider: 'openrouter',
    model: 'openai/gpt-4o',
    inputCostPer1MTokensUsd: 2.50,
    outputCostPer1MTokensUsd: 10.00,
    pricingSource: 'configured',
    lastUpdated: '2025-01-01',
    notes: 'Estimated from OpenRouter public pricing.',
  },
  {
    provider: 'openrouter',
    model: 'anthropic/claude-3.5-sonnet',
    inputCostPer1MTokensUsd: 3.00,
    outputCostPer1MTokensUsd: 15.00,
    pricingSource: 'configured',
    lastUpdated: '2025-01-01',
    notes: 'Estimated from OpenRouter public pricing.',
  },
  {
    provider: 'openrouter',
    model: 'google/gemini-2.0-flash-001',
    inputCostPer1MTokensUsd: 0.10,
    outputCostPer1MTokensUsd: 0.40,
    pricingSource: 'configured',
    lastUpdated: '2025-01-01',
    notes: 'Estimated from OpenRouter public pricing.',
  },
  {
    provider: 'gemini',
    model: 'gemini-1.5-flash',
    inputCostPer1MTokensUsd: 0.075,
    outputCostPer1MTokensUsd: 0.30,
    pricingSource: 'configured',
    lastUpdated: '2025-01-01',
    notes: 'Estimated from Google AI public pricing.',
  },
  {
    provider: 'ollama',
    model: 'qwen2.5:0.5b',
    inputCostPer1MTokensUsd: 0,
    outputCostPer1MTokensUsd: 0,
    pricingSource: 'configured',
    lastUpdated: '2025-01-01',
    notes: 'Local model — no API cost. Hardware electricity cost not estimated.',
  },
  {
    provider: 'ollama',
    model: 'gemma3:1b',
    inputCostPer1MTokensUsd: 0,
    outputCostPer1MTokensUsd: 0,
    pricingSource: 'configured',
    lastUpdated: '2025-01-01',
    notes: 'Local model — no API cost.',
  },
];

/**
 * Look up pricing for a model.
 */
export function getModelPricing(provider: string, model: string): ModelPricing | null {
  const normalizedProvider = provider.toLowerCase();
  const normalizedModel = model.toLowerCase();

  // Exact match
  const exact = PRICING_TABLE.find(
    (p) => p.provider === normalizedProvider && p.model.toLowerCase() === normalizedModel
  );
  if (exact) return exact;

  // Partial match (model name contains)
  const partial = PRICING_TABLE.find(
    (p) => p.provider === normalizedProvider && normalizedModel.includes(p.model.toLowerCase())
  );
  if (partial) return partial;

  return null;
}

/**
 * Check if pricing is known for a model.
 */
export function isPricingKnown(provider: string, model: string): boolean {
  const pricing = getModelPricing(provider, model);
  return pricing !== null && pricing.pricingSource !== 'unknown';
}

/**
 * Get all known pricing entries.
 */
export function getAllPricing(): ModelPricing[] {
  return [...PRICING_TABLE];
}
