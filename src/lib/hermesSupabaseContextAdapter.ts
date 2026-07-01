/**
 * Hermes Supabase Context Adapter — live Supabase queries for Hermes chat context.
 *
 * Queries tables using the authenticated admin session (anon key + RLS).
 * Returns honest results: live data when available, clear error when not.
 * Never exposes service role key. Never fakes data.
 */

import { supabase, isSupabaseConfigured } from './supabaseClient';

export interface SupabaseContextResult {
  liveSupabaseAvailable: boolean;
  reason: string;
  queried: boolean;
  table: string | null;
  data: unknown[] | null;
  rowCount?: number;
  error?: string | null;
}

async function hasSession(): Promise<boolean> {
  if (!supabase || !isSupabaseConfigured) return false;
  try {
    const { data: { session } } = await supabase.auth.getSession();
    return Boolean(session);
  } catch {
    return false;
  }
}

async function queryTable(table: string, limit = 20): Promise<SupabaseContextResult> {
  if (!supabase || !isSupabaseConfigured) {
    return { liveSupabaseAvailable: false, reason: 'Supabase client not configured (missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY).', queried: false, table, data: null };
  }
  if (!(await hasSession())) {
    return { liveSupabaseAvailable: false, reason: 'No authenticated admin session. Log in to access live Supabase data.', queried: false, table, data: null };
  }
  try {
    const { data, error } = await supabase.from(table).select('*').order('created_at', { ascending: false }).limit(limit);
    if (error) {
      return { liveSupabaseAvailable: false, reason: `Query to ${table} failed: ${error.message.slice(0, 100)}`, queried: true, table, data: null, error: error.message };
    }
    const rows = data ?? [];
    return { liveSupabaseAvailable: true, reason: `Live query succeeded on ${table}.`, queried: true, table, data: rows, rowCount: rows.length };
  } catch (e) {
    return { liveSupabaseAvailable: false, reason: `Connection error querying ${table}: ${String(e).slice(0, 80)}`, queried: true, table, data: null, error: String(e) };
  }
}

/** Query Supabase for Hermes context. Returns live data when available. */
export function querySupabaseContext(table: string, _filter?: string): SupabaseContextResult {
  // This is the sync entry point — we return a pending pattern and let the async version handle it.
  // For now, return the honest stub and let the async version below do the real work.
  return {
    liveSupabaseAvailable: false,
    reason: 'Use querySupabaseContextAsync for live queries.',
    queried: false,
    table,
    data: null,
  };
}

/** Async version for live Supabase queries. */
export async function querySupabaseContextAsync(table: string): Promise<SupabaseContextResult> {
  return queryTable(table, 20);
}

/** Check if Supabase is available for Hermes context. */
export async function isSupabaseAvailableAsync(): Promise<boolean> {
  return hasSession();
}

/** Check if Supabase is available (sync — for backward compat). */
export function isSupabaseAvailable(): boolean {
  // Cannot check session synchronously; return configured status as best guess
  return isSupabaseConfigured;
}

/** Get an honest status message about Supabase availability. */
export function getSupabaseStatusMessage(): string {
  if (!isSupabaseConfigured) {
    return 'Supabase is not configured. VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are not set.';
  }
  return 'Supabase client is configured. Live queries require an authenticated admin session.';
}

/** Summary query types for Hermes context. */
export type ContextQueryType =
  | 'approvals_summary'
  | 'ray_review_summary'
  | 'research_summary'
  | 'opportunities_summary'
  | 'offers_summary'
  | 'clients_safe_summary'
  | 'synthetic_client_status'
  | 'reports_summary'
  | 'system_status'
  | 'scheduler_summary'
  | 'trading_paper_summary'
  | 'blockers_summary'
  | 'revenue_summary';

export interface LiveContextSummary {
  ok: boolean;
  sourceType: 'live_supabase' | 'static_fallback' | 'unavailable';
  liveData: boolean;
  generatedAt: string;
  tableNamesUsed: string[];
  rowCounts: Record<string, number>;
  summary: string;
  records: Array<Record<string, unknown>>;
  limitations: string[];
  safetyLevel: 'safe_read_only';
  executionAllowed: false;
}

/** Build a live context summary from Supabase queries. */
export async function getLiveContextSummary(type: ContextQueryType): Promise<LiveContextSummary> {
  const now = new Date().toISOString();
  const base: LiveContextSummary = {
    ok: false,
    sourceType: 'unavailable',
    liveData: false,
    generatedAt: now,
    tableNamesUsed: [],
    rowCounts: {},
    summary: '',
    records: [],
    limitations: [],
    safetyLevel: 'safe_read_only',
    executionAllowed: false as const,
  };

  if (!isSupabaseConfigured) {
    return { ...base, summary: 'Supabase not configured.' };
  }
  if (!(await hasSession())) {
    return { ...base, summary: 'No authenticated admin session. Log in to access live data.' };
  }

  const tableMap: Record<ContextQueryType, { table: string; label: string; filter?: { column: string; value: string } }> = {
    approvals_summary: { table: 'approvals', label: 'approvals', filter: { column: 'status', value: 'pending' } },
    ray_review_summary: { table: 'task_requests', label: 'Ray Review task requests', filter: { column: 'task_type', value: 'ray_review_item' } },
    research_summary: { table: 'research_sources', label: 'research sources' },
    opportunities_summary: { table: 'business_opportunities', label: 'business opportunities' },
    offers_summary: { table: 'monetization_opportunities', label: ' monetization offers' },
    clients_safe_summary: { table: 'client_profiles', label: 'client profiles' },
    synthetic_client_status: { table: 'client_profiles', label: 'client profiles' },
    reports_summary: { table: 'nexus_events', label: 'report events', filter: { column: 'lane', value: 'system' } },
    system_status: { table: 'system_health', label: 'system health' },
    scheduler_summary: { table: 'agent_jobs', label: 'scheduler jobs' },
    trading_paper_summary: { table: 'demo_trades', label: 'demo trades' },
    blockers_summary: { table: 'ops_incidents', label: 'ops incidents' },
    revenue_summary: { table: 'monetization_opportunities', label: 'revenue opportunities' },
  };

  const config = tableMap[type];
  if (!config) return { ...base, summary: `Unknown context type: ${type}` };

  try {
    let query = supabase!.from(config.table).select('*').order('created_at', { ascending: false }).limit(20);
    if (config.filter) {
      query = query.eq(config.filter.column, config.filter.value);
    }
    const { data, error } = await query;

    if (error) {
      return {
        ...base,
        summary: `Query to ${config.table} failed: ${error.message.slice(0, 100)}`,
        limitations: [`RLS or query error on ${config.table}`, 'Verify you are logged in as an active admin'],
      };
    }

    const rows = data ?? [];
    return {
      ok: true,
      sourceType: 'live_supabase',
      liveData: true,
      generatedAt: now,
      tableNamesUsed: [config.table],
      rowCounts: { [config.table]: rows.length },
      summary: `Live Supabase: ${rows.length} ${config.label} found.`,
      records: rows.slice(0, 10),
      limitations: ['Live data from authenticated admin session', 'Row count capped at 20 for safety'],
      safetyLevel: 'safe_read_only',
      executionAllowed: false as const,
    };
  } catch (e) {
    return {
      ...base,
      summary: `Connection error: ${String(e).slice(0, 80)}`,
      limitations: ['Network or auth error'],
    };
  }
}
