/**
 * Live Data Loader — shared live-first data loading for all Nexus OS sections.
 *
 * Pattern: Supabase first → static fallback → honest mismatch report.
 * Every section returns a unified result with source labels and mismatch info.
 */

import { supabase, isSupabaseConfigured } from './supabaseClient';

// ─── Safe helpers for undefined/null fields ───

/** Safely convert any value to a string. Returns fallback for null/undefined. */
export function safeStr(val: unknown, fallback = ''): string {
  if (val == null) return fallback;
  if (typeof val === 'string') return val;
  if (typeof val === 'number' || typeof val === 'boolean') return String(val);
  if (typeof val === 'object') {
    try { return JSON.stringify(val); } catch { return fallback; }
  }
  return fallback;
}

/** Safely call .replace() on a value. Never crashes on undefined/null. */
export function safeReplace(val: unknown, pattern: string | RegExp, replacement: string): string {
  return safeStr(val).replace(pattern, replacement);
}

/** Safe number parse. Returns fallback for non-numeric values. */
export function safeNum(val: unknown, fallback = 0): number {
  if (val == null) return fallback;
  const n = Number(val);
  return Number.isFinite(n) ? n : fallback;
}

// ─── Section Normalizers ───
// Maps raw Supabase rows into the shape each UI component expects.

/** Normalize a research_sources row → research candidate shape. */
export function normalizeResearchRow(row: Record<string, unknown>, index: number): Record<string, unknown> {
  const metadata = (typeof row.metadata === 'object' && row.metadata !== null ? row.metadata : {}) as Record<string, unknown>;
  return {
    id: safeStr(row.id, `research-${index}`),
    title: safeStr(row.title, 'Untitled Research'),
    source: safeStr(row.source_type, 'unknown'),
    type: safeStr(metadata.type, safeStr(row.source_type, 'research')),
    lane: safeStr(metadata.lane, 'research'),
    score: safeNum(row.confidence, safeNum(metadata.score, 50)),
    status: safeStr(metadata.status, 'scored'),
    reason: safeStr(row.why_it_matters, safeStr(row.snippet, 'No reasoning available.')),
    nextAction: safeStr(metadata.nextAction, 'Review and score this candidate'),
    convertOptions: Array.isArray(metadata.convertOptions) ? metadata.convertOptions : ['opportunity', 'content_draft'],
    revenueRange: safeStr(metadata.revenueRange, ''),
    confidence: safeStr(metadata.confidence, ''),
    raw: row,
  };
}

/** Normalize a business_opportunities row → opportunity shape. */
export function normalizeBusinessRow(row: Record<string, unknown>, _index: number): Record<string, unknown> {
  const payload = (typeof row.payload === 'object' && row.payload !== null ? row.payload : {}) as Record<string, unknown>;
  return {
    id: safeStr(row.id),
    title: safeStr(row.title, 'Untitled Opportunity'),
    summary: safeStr(row.summary, safeStr(payload.summary, '')),
    score: safeNum(row.score, safeNum(payload.score, 0)),
    status: safeStr(row.status, 'open'),
    category: safeStr(row.category, safeStr(payload.category, 'uncategorized')),
    type: safeStr(row.category, safeStr(payload.category, 'opportunity')),
    revenueRange: safeStr(payload.revenueRange, ''),
    confidence: safeStr(payload.confidence, ''),
    source: safeStr(row.source, safeStr(row.source_concept, 'supabase')),
    recommended_next_action: safeStr(row.recommended_next_action, ''),
    raw: row,
  };
}

/** Normalize a monetization_opportunities row → monetization shape. */
export function normalizeMonetizationRow(row: Record<string, unknown>, _index: number): Record<string, unknown> {
  return {
    id: safeStr(row.id),
    title: safeStr(row.title, 'Untitled Offer'),
    summary: safeStr(row.source_summary, ''),
    status: safeStr(row.status, 'open'),
    category: safeStr(row.fit_with_goclear, 'general'),
    type: 'monetization',
    score: safeNum(row.overall_score, safeNum(row.confidence, 0)),
    confidence: safeStr(row.confidence, ''),
    revenueRange: safeStr(row.smallest_test, ''),
    moneyAngle: safeStr(row.money_angle, ''),
    raw: row,
  };
}

/** Normalize a client_profiles row → client shape. */
export function normalizeClientRow(row: Record<string, unknown>, _index: number): Record<string, unknown> {
  return {
    id: safeStr(row.id),
    title: safeStr(row.client_label, safeStr(row.title, 'Untitled Client')),
    summary: safeStr(row.next_required_action, safeStr(row.summary, '')),
    status: safeStr(row.current_stage, safeStr(row.status, 'unknown')),
    category: safeStr(row.category, 'client'),
    type: 'client',
    score: safeNum(row.score, safeNum(row.progress_percentage, 0)),
    raw: row,
  };
}

/** Normalize a task_requests (ray_review) row → review card shape. */
export function normalizeRayReviewRow(row: Record<string, unknown>, _index: number): Record<string, unknown> {
  const payload = (typeof row.payload === 'object' && row.payload !== null ? row.payload : {}) as Record<string, unknown>;
  return {
    id: safeStr(row.id),
    title: safeStr(payload.title, safeStr(row.task_type, 'Ray Review Item')),
    summary: safeStr(payload.summary, safeStr(payload.description, '')),
    status: safeStr(row.status, 'requested'),
    category: safeStr(payload.category, safeStr(row.task_type, 'review')),
    type: safeStr(row.task_type, 'ray_review_item'),
    score: safeNum(payload.score, 0),
    raw: row,
  };
}

/** Normalize any section's rows based on sectionId. */
export function normalizeRows(sectionId: string, rows: Record<string, unknown>[]): Record<string, unknown>[] {
  const normalizers: Record<string, (row: Record<string, unknown>, i: number) => Record<string, unknown>> = {
    research_engine: normalizeResearchRow,
    business_opportunities: normalizeBusinessRow,
    monetization: normalizeMonetizationRow,
    clients: normalizeClientRow,
    ray_review: normalizeRayReviewRow,
  };
  const fn = normalizers[sectionId];
  if (!fn) return rows;
  return rows.map((row, i) => fn(row, i));
}

export type SourceType = 'live_supabase' | 'static_fallback' | 'report_snapshot' | 'localStorage_only' | 'unavailable';

export interface SectionResult<T> {
  ok: boolean;
  sectionId: string;
  sourceType: SourceType;
  liveData: boolean;
  tableNamesUsed: string[];
  rowCount: number;
  staticCount: number;
  generatedAt: string;
  lastLoadedAt: string;
  records: T[];
  fallbackRecords: T[];
  limitations: string[];
  mismatch: string | null;
  error: string | null;
}

async function hasSession(): Promise<boolean> {
  if (!supabase || !isSupabaseConfigured) return false;
  try {
    const { data: { session } } = await supabase.auth.getSession();
    return Boolean(session);
  } catch { return false; }
}

async function queryTable(
  table: string,
  opts: { limit?: number; order?: string; ascending?: boolean; filters?: Array<{ column: string; value: string }> } = {},
): Promise<{ data: unknown[]; error: string | null; count: number }> {
  if (!supabase) return { data: [], error: 'Supabase not configured', count: 0 };
  try {
    let q = supabase.from(table).select('*');
    if (opts.filters) for (const f of opts.filters) q = q.eq(f.column, f.value);
    q = q.order(opts.order ?? 'created_at', { ascending: opts.ascending ?? false });
    if (opts.limit) q = q.limit(opts.limit);
    const { data, error } = await q;
    if (error) return { data: [], error: error.message, count: 0 };
    return { data: data ?? [], error: null, count: (data ?? []).length };
  } catch (e) { return { data: [], error: String(e), count: 0 }; }
}

function buildResult<T>(
  sectionId: string, sourceType: SourceType, liveData: boolean,
  records: T[], fallbackRecords: T[], tableNamesUsed: string[],
  limitations: string[], mismatch: string | null, error: string | null,
): SectionResult<T> {
  return {
    ok: sourceType === 'live_supabase',
    sectionId, sourceType, liveData, tableNamesUsed,
    rowCount: records.length, staticCount: fallbackRecords.length,
    generatedAt: new Date().toISOString(),
    lastLoadedAt: new Date().toISOString(),
    records, fallbackRecords, limitations, mismatch, error,
  };
}

// ─── Section Loaders ───

export async function loadSectionData<T extends Record<string, unknown>>(
  sectionId: string,
  staticData: T[],
  tableConfig: {
    table: string;
    fallbackLabel?: string;
    limit?: number;
    filters?: Array<{ column: string; value: string }>;
    idField?: string;
    titleField?: string;
  },
): Promise<SectionResult<T>> {
  const fallbackLabel = tableConfig.fallbackLabel ?? 'static snapshot';
  const limits = { limit: tableConfig.limit ?? 100 };

  if (!supabase || !isSupabaseConfigured) {
    return buildResult(sectionId, 'static_fallback', false, staticData, staticData, [],
      ['Supabase not configured'], null, null);
  }

  const session = await hasSession();
  if (!session) {
    return buildResult(sectionId, 'static_fallback', false, staticData, staticData, [],
      ['No auth session'], null, null);
  }

  const { data: liveRows, error } = await queryTable(tableConfig.table, {
    limit: limits.limit, filters: tableConfig.filters,
  });

  if (error) {
    return buildResult(sectionId, 'static_fallback', false, staticData, staticData, [tableConfig.table],
      [`Query error: ${error.slice(0, 80)}`], null, error);
  }

  const rows = liveRows as T[];

  if (rows.length === 0 && staticData.length > 0) {
    const mismatch = `Page has ${staticData.length} static items, Supabase has 0 live rows in ${tableConfig.table}.`;
    return buildResult(sectionId, 'static_fallback', false, staticData, staticData, [tableConfig.table],
      [`0 rows in Supabase; using ${fallbackLabel} fallback`], mismatch, null);
  }

  if (rows.length === 0 && staticData.length === 0) {
    return buildResult(sectionId, 'unavailable', false, [], [], [tableConfig.table],
      ['No data available'], null, null);
  }

  if (rows.length > 0) {
    const normalized = normalizeRows(sectionId, rows as Record<string, unknown>[]) as T[];
    return buildResult(sectionId, 'live_supabase', true, normalized, staticData, [tableConfig.table],
      [`Live data from ${tableConfig.table}`], null, null);
  }

  return buildResult(sectionId, 'static_fallback', false, staticData, staticData, [tableConfig.table],
    ['Unexpected state'], null, null);
}

// ─── Section Configs ───

export const SECTION_CONFIGS: Record<string, {
  table: string;
  fallbackLabel: string;
  limit?: number;
  filters?: Array<{ column: string; value: string }>;
}> = {
  ray_review: { table: 'task_requests', fallbackLabel: 'Ray Review cards', limit: 100, filters: [{ column: 'task_type', value: 'ray_review_item' }] },
  business_opportunities: { table: 'business_opportunities', fallbackLabel: 'Business Opportunities', limit: 100 },
  research_engine: { table: 'research_sources', fallbackLabel: 'Research Candidates', limit: 100 },
  monetization: { table: 'monetization_opportunities', fallbackLabel: 'Monetization Offers', limit: 100 },
  clients: { table: 'client_profiles', fallbackLabel: 'Client Profiles', limit: 100 },
  credit_funding: { table: 'business_opportunities', fallbackLabel: 'Credit & Funding Data', limit: 50, filters: [{ column: 'category', value: 'credit_offer' }] },
  trading_demo: { table: 'trading_strategy_candidates', fallbackLabel: 'Trading Strategies', limit: 50 },
  reports: { table: 'nexus_events', fallbackLabel: 'Report Registry', limit: 50, filters: [{ column: 'lane', value: 'system' }] },
  system_health: { table: 'system_health', fallbackLabel: 'System Health', limit: 50 },
  automation: { table: 'agent_jobs', fallbackLabel: 'Automation Schedule', limit: 50 },
  cli_registry: { table: 'agent_jobs', fallbackLabel: 'CLI Registry', limit: 50 },
  settings: { table: 'settings', fallbackLabel: 'Settings', limit: 50 },
};

/** Load data for any section by ID. */
export async function loadSection<T extends Record<string, unknown>>(
  sectionId: string,
  staticData: T[],
): Promise<SectionResult<T>> {
  const config = SECTION_CONFIGS[sectionId];
  if (!config) {
    return buildResult(sectionId, 'static_fallback', false, staticData, staticData, [],
      ['No section config found'], null, null);
  }
  return loadSectionData(sectionId, staticData, config);
}

/** Count live rows in a table without loading full data. */
export async function countLive(table: string): Promise<{ count: number; source: string; sourceLabel: string }> {
  if (!supabase || !isSupabaseConfigured) {
    return { count: 0, source: 'unavailable', sourceLabel: 'Supabase not configured' };
  }
  const session = await hasSession();
  if (!session) {
    return { count: 0, source: 'unavailable', sourceLabel: 'No auth session' };
  }
  try {
    const { count, error } = await supabase.from(table).select('*', { count: 'exact', head: true });
    if (error) return { count: 0, source: 'unavailable', sourceLabel: `Query error: ${error.message}` };
    return { count: count ?? 0, source: 'live_supabase', sourceLabel: `Live count from ${table}` };
  } catch (e) {
    return { count: 0, source: 'unavailable', sourceLabel: `Error: ${String(e)}` };
  }
}
