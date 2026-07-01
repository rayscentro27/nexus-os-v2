/**
 * Hermes Model Usage Ledger — logs every model call attempt.
 *
 * Stored in localStorage (browser-safe). Used to answer:
 * - "Did you use a model for that?"
 * - "Why did you use the expensive model?"
 * - "What is using tokens?"
 * - "Did any background job use a model?"
 * - "What was skipped to save cost?"
 *
 * Never logs: secrets, raw prompts, full .env, private keys, PII.
 */

export interface UsageEntry {
  id: string;
  timestamp: string;
  route: string;
  modelProvider: string;
  modelName: string;
  promptType: string;
  estimatedInputTokens: number;
  estimatedOutputTokens: number;
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
 * Log a model call attempt.
 */
export function logModelAttempt(entry: Omit<UsageEntry, 'id' | 'timestamp'>): UsageEntry {
  const full: UsageEntry = {
    ...entry,
    id: generateId(),
    timestamp: new Date().toISOString(),
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
 * Get total estimated tokens used across all logged calls.
 */
export function getTotalTokensUsed(): { input: number; output: number; calls: number } {
  const entries = getUsageEntries();
  let input = 0;
  let output = 0;
  let calls = 0;
  for (const e of entries) {
    if (e.wasModelCalled) {
      input += e.estimatedInputTokens;
      output += e.estimatedOutputTokens;
      calls++;
    }
  }
  return { input, output, calls };
}

/**
 * Get recent usage summary for status answers.
 */
export function getRecentUsageSummary(lastN = 5): string {
  const entries = getStoredEntries().slice(-lastN);
  if (entries.length === 0) return 'No model usage logged yet.';

  return entries.map((e) => {
    const time = new Date(e.timestamp).toLocaleTimeString();
    if (e.wasModelCalled) {
      return `${time}: ${e.route} via ${e.modelProvider}/${e.modelName} (~${e.estimatedInputTokens} tokens in, ~${e.estimatedOutputTokens} out)`;
    }
    return `${time}: ${e.route} — skipped: ${e.skippedReason}`;
  }).join('\n');
}

/**
 * Get answer to "What did the model do recently?"
 */
export function getModelActivityAnswer(): string {
  const { input, output, calls } = getTotalTokensUsed();
  if (calls === 0) return 'No model calls have been made yet. All answers have been from local context and Supabase data.';

  const entries = getStoredEntries();
  const recent = entries.filter((e) => e.wasModelCalled).slice(-3);
  const breakdown = recent.map((e) => `• ${e.promptType}: ${e.modelProvider}/${e.modelName} (~${e.estimatedInputTokens} tokens)`).join('\n');

  return `Model usage summary:\n• Total calls: ${calls}\n• Total estimated input tokens: ~${input}\n• Total estimated output tokens: ~${output}\n\nRecent calls:\n${breakdown}`;
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
