/**
 * Live Data Loader — shared live-first data loading for all Nexus OS sections.
 *
 * Pattern: Supabase first → static fallback → honest mismatch report.
 * Every section returns a unified result with source labels and mismatch info.
 */

import { supabase, isSupabaseConfigured } from './supabaseClient';

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
    return buildResult(sectionId, 'live_supabase', true, rows, staticData, [tableConfig.table],
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
