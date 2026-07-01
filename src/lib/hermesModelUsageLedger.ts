/**
 * Hermes Model Usage Ledger — logs every model call attempt.
 *
 * Stored in localStorage (browser-safe). Used to answer:
 * - "Did you use a model for that?"
 * - "Why did you use the expensive model?"
 * - "What is using tokens?"
 * - "Did any background job use a model?"
 * - "What was skipped to save cost?"
 * - "What did that model call cost?"
 * - "Was that model call necessary?"
 * - "How can we reduce token cost?"
 *
 * Never logs: secrets, raw prompts, full .env, private keys, PII.
 */

import { estimateModelCallCost } from './hermesModelCostEstimator';
import { getCostAdvice } from './hermesModelCostAdvisor';

export interface UsageEntry {
  id: string;
  timestamp: string;
  route: string;
  modelProvider: string;
  modelName: string;
  promptType: string;
  estimatedInputTokens: number;
  estimatedOutputTokens: number;
  estimatedTotalTokens: number;
  estimatedInputCostUsd: number;
  estimatedOutputCostUsd: number;
  estimatedTotalCostUsd: number;
  costKnown: boolean;
  costConfidence: string;
  costReductionAdvice: string;
  wasModelNecessary: boolean;
  cheaperAlternativeRoute: string;
  whyRouteChosen: string;
  contextSources: string[];
  wasModelCalled: boolean;
  skippedReason: string;
  fallbackUsed: string;
  costEstimateAvailable: boolean;
  error: string;
  durationMs: number;
}

const STORAGE_KEY = 'nexus-hermes-model-usage-v1';
const MAX_ENTRIES = 200;

function generateId(): string {
  return `usage-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function getStoredEntries(): UsageEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(-MAX_ENTRIES) : [];
  } catch {
    return [];
  }
}

function persistEntries(entries: UsageEntry[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries.slice(-MAX_ENTRIES)));
  } catch {
    // localStorage full or unavailable — silently drop
  }
}

/**
 * Log a model call attempt with cost estimates.
 */
export function logModelAttempt(entry: Omit<UsageEntry, 'id' | 'timestamp' | 'estimatedTotalTokens' | 'estimatedInputCostUsd' | 'estimatedOutputCostUsd' | 'estimatedTotalCostUsd' | 'costKnown' | 'costConfidence' | 'costReductionAdvice' | 'wasModelNecessary' | 'cheaperAlternativeRoute' | 'whyRouteChosen'>): UsageEntry {
  // Calculate cost estimates
  const cost = estimateModelCallCost({
    provider: entry.modelProvider,
    model: entry.modelName,
    estimatedInputTokens: entry.estimatedInputTokens,
    estimatedOutputTokens: entry.estimatedOutputTokens,
    route: entry.route,
  });

  // Get cost advice
  const advice = getCostAdvice({
    route: entry.route,
    reason: entry.skippedReason || entry.promptType,
    provider: entry.modelProvider,
    model: entry.modelName,
    estimatedInputTokens: entry.estimatedInputTokens,
    estimatedOutputTokens: entry.estimatedOutputTokens,
    wasModelCalled: entry.wasModelCalled,
  });

  const full: UsageEntry = {
    ...entry,
    id: generateId(),
    timestamp: new Date().toISOString(),
    estimatedTotalTokens: entry.estimatedInputTokens + entry.estimatedOutputTokens,
    estimatedInputCostUsd: cost.estimatedInputCostUsd,
    estimatedOutputCostUsd: cost.estimatedOutputCostUsd,
    estimatedTotalCostUsd: cost.estimatedTotalCostUsd,
    costKnown: cost.costKnown,
    costConfidence: cost.confidence,
    costReductionAdvice: advice.summary,
    wasModelNecessary: advice.wasNecessary,
    cheaperAlternativeRoute: advice.cheaperAlternative,
    whyRouteChosen: entry.skippedReason || entry.promptType,
  };
  const entries = getStoredEntries();
  entries.push(full);
  persistEntries(entries);
  return full;
}

/**
 * Log a skipped no-model decision.
 */
export function logModelSkipped(reason: string, promptType: string): UsageEntry {
  return logModelAttempt({
    route: 'no_model',
    modelProvider: 'none',
    modelName: 'none',
    promptType,
    estimatedInputTokens: 0,
    estimatedOutputTokens: 0,
    contextSources: [],
    wasModelCalled: false,
    skippedReason: reason,
    fallbackUsed: '',
    costEstimateAvailable: false,
    error: '',
    durationMs: 0,
  });
}

/**
 * Get all usage entries (for Hermes status answers).
 */
export function getUsageEntries(): UsageEntry[] {
  return getStoredEntries();
}

/**
 * Get total estimated tokens and cost used across all logged calls.
 */
export function getTotalTokensUsed(): { input: number; output: number; calls: number; totalCostUsd: number } {
  const entries = getUsageEntries();
  let input = 0;
  let output = 0;
  let calls = 0;
  let totalCostUsd = 0;
  for (const e of entries) {
    if (e.wasModelCalled) {
      input += e.estimatedInputTokens;
      output += e.estimatedOutputTokens;
      calls++;
      totalCostUsd += e.estimatedTotalCostUsd || 0;
    }
  }
  return { input, output, calls, totalCostUsd };
}

/**
 * Get recent usage summary with cost for status answers.
 */
export function getRecentUsageSummary(lastN = 5): string {
  const entries = getStoredEntries().slice(-lastN);
  if (entries.length === 0) return 'No model usage logged yet.';

  return entries.map((e) => {
    const time = new Date(e.timestamp).toLocaleTimeString();
    if (e.wasModelCalled) {
      const costStr = e.costKnown
        ? ` est. $${(e.estimatedTotalCostUsd || 0).toFixed(4)}`
        : ' pricing unknown';
      return `${time}: ${e.route} via ${e.modelProvider}/${e.modelName} (~${e.estimatedInputTokens} in, ~${e.estimatedOutputTokens} out)${costStr}`;
    }
    return `${time}: ${e.route} — skipped: ${e.skippedReason}`;
  }).join('\n');
}

/**
 * Get answer to "What did the model do recently?" with cost info.
 */
export function getModelActivityAnswer(): string {
  const { input, output, calls, totalCostUsd } = getTotalTokensUsed();
  if (calls === 0) return 'No model calls have been made yet. All answers have been from local context and Supabase data.';

  const entries = getStoredEntries();
  const recent = entries.filter((e) => e.wasModelCalled).slice(-3);
  const breakdown = recent.map((e) => {
    const costStr = e.costKnown
      ? ` est. $${(e.estimatedTotalCostUsd || 0).toFixed(4)}`
      : ' pricing unknown';
    return `• ${e.promptType}: ${e.modelProvider}/${e.modelName} (~${e.estimatedInputTokens} in, ~${e.estimatedOutputTokens} out)${costStr}`;
  }).join('\n');

  const costStr = totalCostUsd > 0
    ? `\n• Total estimated cost: $${totalCostUsd.toFixed(4)}`
    : '';

  return `Model usage summary:\n• Total calls: ${calls}\n• Total estimated input tokens: ~${input}\n• Total estimated output tokens: ~${output}${costStr}\n\nRecent calls:\n${breakdown}`;
}

/**
 * Clear all usage entries.
 */
export function clearUsageLog(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // silently drop
  }
}
