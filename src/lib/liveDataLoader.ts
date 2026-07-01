/**
 * Live Data Loader — shared utility for loading data from Supabase with static fallback.
 *
 * Every section uses this pattern:
 * 1. Try Supabase query (authenticated admin session, RLS-gated)
 * 2. If Supabase unavailable or returns empty, fall back to static data
 * 3. Return data + source label so UI can show "Live Supabase" or "Static fallback"
 */

import { supabase, isSupabaseConfigured } from './supabaseClient';

export type DataSource = 'live_supabase' | 'static_fallback' | 'local_only' | 'unavailable';

export interface LiveResult<T> {
  data: T[];
  source: DataSource;
  sourceLabel: string;
  rowCount: number;
  error: string | null;
  timestamp: string;
}

export interface LiveCount {
  count: number;
  source: DataSource;
  sourceLabel: string;
  error: string | null;
}

/** Check if Supabase is connected and we have an auth session. */
export async function isLiveConnected(): Promise<boolean> {
  if (!supabase || !isSupabaseConfigured) return false;
  try {
    const { data: { session } } = await supabase.auth.getSession();
    return Boolean(session);
  } catch {
    return false;
  }
}

/** Load rows from a Supabase table with fallback to static data. */
export async function loadLive<T extends Record<string, unknown>>(
  table: string,
  staticData: T[],
  opts: {
    limit?: number;
    order?: string;
    ascending?: boolean;
    filters?: Array<{ column: string; value: string | number | boolean }>;
    fallbackLabel?: string;
  } = {},
): Promise<LiveResult<T>> {
  const timestamp = new Date().toISOString();
  const fallbackLabel = opts.fallbackLabel ?? 'static snapshot';

  if (!supabase || !isSupabaseConfigured) {
    return {
      data: staticData,
      source: 'static_fallback',
      sourceLabel: `${fallbackLabel} · Supabase not configured`,
      rowCount: staticData.length,
      error: null,
      timestamp,
    };
  }

  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      return {
        data: staticData,
        source: 'static_fallback',
        sourceLabel: `${fallbackLabel} · No auth session`,
        rowCount: staticData.length,
        error: null,
        timestamp,
      };
    }

    let query = supabase.from(table).select('*');
    if (opts.filters) {
      for (const f of opts.filters) {
        query = query.eq(f.column, f.value);
      }
    }
    query = query.order(opts.order ?? 'created_at', { ascending: opts.ascending ?? false });
    if (opts.limit) query = query.limit(opts.limit);

    const { data, error } = await query;

    if (error) {
      return {
        data: staticData,
        source: 'static_fallback',
        sourceLabel: `${fallbackLabel} · Query error: ${error.message.slice(0, 60)}`,
        rowCount: staticData.length,
        error: error.message,
        timestamp,
      };
    }

    const rows = (data ?? []) as T[];
    if (rows.length === 0) {
      return {
        data: staticData,
        source: 'static_fallback',
        sourceLabel: `${fallbackLabel} · 0 rows in Supabase (using fallback)`,
        rowCount: staticData.length,
        error: null,
        timestamp,
      };
    }

    return {
      data: rows,
      source: 'live_supabase',
      sourceLabel: `Live Supabase · ${rows.length} rows from ${table}`,
      rowCount: rows.length,
      error: null,
      timestamp,
    };
  } catch (e) {
    return {
      data: staticData,
      source: 'static_fallback',
      sourceLabel: `${fallbackLabel} · Connection error`,
      rowCount: staticData.length,
      error: String(e),
      timestamp,
    };
  }
}

/** Count rows in a Supabase table. */
export async function countLive(table: string): Promise<LiveCount> {
  if (!supabase || !isSupabaseConfigured) {
    return { count: 0, source: 'unavailable', sourceLabel: 'Supabase not configured', error: null };
  }
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      return { count: 0, source: 'unavailable', sourceLabel: 'No auth session', error: null };
    }
    const { count, error } = await supabase.from(table).select('*', { count: 'exact', head: true });
    if (error) {
      return { count: 0, source: 'unavailable', sourceLabel: `Query error: ${error.message.slice(0, 40)}`, error: error.message };
    }
    return { count: count ?? 0, source: 'live_supabase', sourceLabel: `Live · ${count ?? 0} rows`, error: null };
  } catch (e) {
    return { count: 0, source: 'unavailable', sourceLabel: 'Connection error', error: String(e) };
  }
}

/** Write a decision to Supabase (update existing row). */
export async function persistDecision(
  table: string,
  id: string,
  updates: Record<string, unknown>,
): Promise<{ ok: boolean; error: string | null; source: DataSource }> {
  if (!supabase || !isSupabaseConfigured) {
    return { ok: false, error: 'Supabase not configured', source: 'unavailable' };
  }
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      return { ok: false, error: 'No auth session', source: 'unavailable' };
    }
    const { error } = await supabase.from(table).update(updates).eq('id', id);
    if (error) {
      return { ok: false, error: error.message, source: 'live_supabase' };
    }
    return { ok: true, error: null, source: 'live_supabase' };
  } catch (e) {
    return { ok: false, error: String(e), source: 'unavailable' };
  }
}

/** Insert a row into Supabase. */
export async function insertRow(
  table: string,
  row: Record<string, unknown>,
): Promise<{ ok: boolean; id: string | null; error: string | null; source: DataSource }> {
  if (!supabase || !isSupabaseConfigured) {
    return { ok: false, id: null, error: 'Supabase not configured', source: 'unavailable' };
  }
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      return { ok: false, id: null, error: 'No auth session', source: 'unavailable' };
    }
    const { data, error } = await supabase.from(table).insert(row).select('id').single();
    if (error) {
      return { ok: false, id: null, error: error.message, source: 'live_supabase' };
    }
    return { ok: true, id: data?.id ?? null, error: null, source: 'live_supabase' };
  } catch (e) {
    return { ok: false, id: null, error: String(e), source: 'unavailable' };
  }
}
