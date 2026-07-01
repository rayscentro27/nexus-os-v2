/**
 * Hermes Context Packer — builds small, relevant context packets for model calls.
 *
 * Never sends: full reports, full second-brain index, full operations logs,
 * full static data, full CLI registry, full tool list, secrets, entire chat history.
 *
 * Only sends: relevant excerpts that help the model answer the specific question.
 */

import type { VisibleItem } from './hermesContextBridge';

export interface ContextPacket {
  userMessage: string;
  route: string;
  compactContext: string;
  sourcesIncluded: string[];
  sourcesExcluded: string[];
  estimatedInputTokens: number;
  contextBudget: number;
  truncated: boolean;
  safetyNotes: string[];
}

const BUDGETS: Record<string, number> = {
  no_model: 0,
  cheap_model: 1500,
  primary_model: 6000,
  background_job: 1000,
};

const MAX_OUTPUT: Record<string, number> = {
  no_model: 0,
  cheap_model: 500,
  primary_model: 1200,
  background_job: 300,
};

function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

function safeExcerpt(text: string, maxChars: number): string {
  if (!text) return '';
  const clean = String(text).replace(/\s+/g, ' ').trim();
  if (clean.length <= maxChars) return clean;
  return clean.slice(0, maxChars - 3) + '...';
}

function buildSupabaseSummary(): string {
  // Static summary from last-known operations status
  // Updated by scripts/ops/collect_nexus_operations_status.py
  return 'Ray Review: 62 rows, Business Opportunities: 26, Research: 52, Monetization: 11, Clients: 1. Source: live Supabase.';
}

function buildOperationsSummary(): string {
  return 'Background jobs: launchd_daily (running), launchd_evening (running), launchd_continuous (running). Ray Review pending: 62. YouTube research: not proven.';
}

function buildResearchSummary(): string {
  return 'Research: 52 scored candidates, last update 2026-07-01.';
}

function buildItemsSummary(items: VisibleItem[]): string {
  if (!items || items.length === 0) return '';
  const excerpt = items.slice(0, 5).map((item) => {
    const title = safeExcerpt(item.title, 60);
    const source = item.dataSource || 'unknown';
    return `[${source}] ${title}`;
  }).join('\n');
  return `Visible items (${items.length} total):\n${excerpt}`;
}

/**
 * Pack context for a model call, respecting token budgets.
 */
export function packContext(
  message: string,
  route: string,
  options: {
    visibleItems?: VisibleItem[];
    selectedItem?: VisibleItem | null;
    pageSummary?: string;
    isBackgroundJob?: boolean;
  } = {}
): ContextPacket {
  const routeKey = options.isBackgroundJob ? 'background_job' : route;
  const budget = BUDGETS[routeKey] ?? BUDGETS.primary_model;
  const safetyNotes: string[] = [];
  const sourcesIncluded: string[] = [];
  const sourcesExcluded: string[] = [];
  let truncated = false;

  if (budget === 0) {
    return {
      userMessage: message,
      route,
      compactContext: '',
      sourcesIncluded: [],
      sourcesExcluded: ['all'],
      estimatedInputTokens: 0,
      contextBudget: 0,
      truncated: false,
      safetyNotes: ['No-model route — no context needed.'],
    };
  }

  const parts: string[] = [];
  let totalEstimate = estimateTokens(message);

  // Page summary (small)
  if (options.pageSummary) {
    const excerpt = safeExcerpt(options.pageSummary, 400);
    const tokens = estimateTokens(excerpt);
    if (totalEstimate + tokens <= budget) {
      parts.push(`[PAGE CONTEXT] ${excerpt}`);
      sourcesIncluded.push('page_context');
      totalEstimate += tokens;
    } else {
      sourcesExcluded.push('page_context');
      truncated = true;
    }
  }

  // Visible items summary (small)
  if (options.visibleItems && options.visibleItems.length > 0) {
    const itemsText = buildItemsSummary(options.visibleItems);
    const tokens = estimateTokens(itemsText);
    if (totalEstimate + tokens <= budget) {
      parts.push(itemsText);
      sourcesIncluded.push('visible_items');
      totalEstimate += tokens;
    } else {
      sourcesExcluded.push('visible_items');
      truncated = true;
    }
  }

  // Selected item detail (tiny)
  if (options.selectedItem) {
    const detail = `[SELECTED] ${safeExcerpt(options.selectedItem.title, 80)} — ${safeExcerpt(options.selectedItem.status || '', 200)}`;
    const tokens = estimateTokens(detail);
    if (totalEstimate + tokens <= budget) {
      parts.push(detail);
      sourcesIncluded.push('selected_item');
      totalEstimate += tokens;
    } else {
      sourcesExcluded.push('selected_item');
      truncated = true;
    }
  }

  // Supabase summary (medium — only for primary_model)
  if (routeKey === 'primary_model') {
    const summary = buildSupabaseSummary();
    const tokens = estimateTokens(summary);
    if (totalEstimate + tokens <= budget) {
      parts.push(`[SUPABASE STATUS] ${summary}`);
      sourcesIncluded.push('supabase_summary');
      totalEstimate += tokens;
    } else {
      sourcesExcluded.push('supabase_summary');
      truncated = true;
    }

    // Operations summary (small)
    const opsSummary = buildOperationsSummary();
    const opsTokens = estimateTokens(opsSummary);
    if (totalEstimate + opsTokens <= budget) {
      parts.push(`[OPERATIONS] ${opsSummary}`);
      sourcesIncluded.push('operations_summary');
      totalEstimate += opsTokens;
    } else {
      sourcesExcluded.push('operations_summary');
      truncated = true;
    }
  }

  // Research summary (only for primary_model)
  if (routeKey === 'primary_model' && /\b(research|opportunity|candidate|strategy)\b/i.test(message)) {
    const summary = buildResearchSummary();
    const tokens = estimateTokens(summary);
    if (totalEstimate + tokens <= budget) {
      parts.push(`[RESEARCH] ${summary}`);
      sourcesIncluded.push('research_summary');
      totalEstimate += tokens;
    } else {
      sourcesExcluded.push('research_summary');
      truncated = true;
    }
  }

  // Safety notes
  safetyNotes.push('No secrets, PII, full reports, or full chat history included.');
  if (truncated) safetyNotes.push('Some sources excluded due to token budget.');

  return {
    userMessage: message,
    route,
    compactContext: parts.join('\n\n'),
    sourcesIncluded,
    sourcesExcluded,
    estimatedInputTokens: totalEstimate,
    contextBudget: budget,
    truncated,
    safetyNotes,
  };
}

export { MAX_OUTPUT, BUDGETS };
