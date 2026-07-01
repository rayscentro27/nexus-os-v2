/**
 * Hermes Supabase Access State — single source for Supabase availability.
 *
 * 5 distinct states:
 *  - available: configured + authenticated + rows exist
 *  - blocked-by-auth: configured but no authenticated session
 *  - blocked-by-RLS: configured + authenticated but RLS blocks the table
 *  - table-empty: configured + authenticated + RLS passes but table has 0 rows
 *  - not-used: page/table not Supabase-backed (uses static/report data)
 *
 * NEVER say "gated" — always report the specific state.
 */

import { isSupabaseConfigured, supabase } from './supabaseClient';

export type SupabaseAccessState =
  | 'available'
  | 'blocked-by-auth'
  | 'blocked-by-RLS'
  | 'table-empty'
  | 'not-used'
  | 'not-configured';

export interface SupabaseStateResult {
  state: SupabaseAccessState;
  table?: string;
  rowCount?: number;
  detail: string;
  userFacing: string;
  source: 'live_query' | 'static_check' | 'page_context';
}

const SUPABASE_BACKED_TABLES = new Set([
  'approvals', 'task_requests', 'nexus_events', 'research_sources',
  'research_runs', 'client_profiles', 'business_opportunities',
  'monetization_opportunities', 'system_health', 'ops_incidents',
  'agent_jobs', 'ray_review_items',
]);

/** Check if a table is Supabase-backed. */
export function isTableSupabaseBacked(table: string): boolean {
  return SUPABASE_BACKED_TABLES.has(table);
}

/** Check auth state without querying data. */
async function checkAuthState(): Promise<{ authenticated: boolean; error?: string }> {
  if (!supabase || !isSupabaseConfigured) return { authenticated: false, error: 'Supabase not configured' };
  try {
    const { data: { session }, error } = await supabase.auth.getSession();
    if (error) return { authenticated: false, error: error.message };
    return { authenticated: Boolean(session) };
  } catch (e) {
    return { authenticated: false, error: String(e) };
  }
}

/** Query a table and return its access state. */
export async function getSupabaseAccessState(
  table: string,
  fallbackContext?: string
): Promise<SupabaseStateResult> {
  // A non-backed section is "not used" regardless of auth state.
  if (!isTableSupabaseBacked(table)) {
    return {
      state: 'not-used', table,
      detail: `Table "${table}" is not a supported live table. This section uses ${fallbackContext || 'static/report data'}.`,
      userFacing: `This question does not use Supabase. It uses ${fallbackContext || 'local bundled data'}.`,
      source: 'page_context',
    };
  }
  // Not configured at all
  if (!isSupabaseConfigured || !supabase) {
    return {
      state: 'not-configured',
      table,
      detail: 'VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are not set.',
      userFacing: 'Supabase is not configured in this environment.',
      source: 'static_check',
    };
  }

  // Check auth first
  const auth = await checkAuthState();
  if (!auth.authenticated) {
    return {
      state: 'blocked-by-auth',
      table,
      detail: auth.error || 'No authenticated session.',
      userFacing: 'Supabase is available but you are not logged in. Log in to access live data.',
      source: 'static_check',
    };
  }

  // Query the table
  try {
    const { data, error } = await supabase
      .from(table)
      .select('*', { count: 'exact', head: true });

    if (error) {
      // RLS blocks access
      if (error.message?.includes('permission') || error.code === '42501' || error.message?.includes('RLS')) {
        return {
          state: 'blocked-by-RLS',
          table,
          detail: `RLS policy blocks access to "${table}": ${error.message}`,
          userFacing: `I can see that "${table}" exists in Supabase, but the current role does not have permission to read it. This is expected for non-admin sessions.`,
          source: 'live_query',
        };
      }
      return {
        state: 'blocked-by-RLS',
        table,
        detail: `Query error on "${table}": ${error.message}`,
        userFacing: `There was an issue reading "${table}" from Supabase.`,
        source: 'live_query',
      };
    }

    const count = data?.length ?? 0;
    if (count === 0) {
      return {
        state: 'table-empty',
        table,
        rowCount: 0,
        detail: `Table "${table}" exists and is accessible but has 0 rows.`,
        userFacing: `I can read "${table}" from Supabase, but it currently has no rows. The section may show static fallback data.`,
        source: 'live_query',
      };
    }

    return {
      state: 'available',
      table,
      rowCount: count,
      detail: `Table "${table}" is live with ${count} rows.`,
      userFacing: `Live Supabase data available: ${count} rows in "${table}".`,
      source: 'live_query',
    };
  } catch (e) {
    return {
      state: 'blocked-by-RLS',
      table,
      detail: `Unexpected error querying "${table}": ${String(e)}`,
      userFacing: `Could not query "${table}" from Supabase.`,
      source: 'live_query',
    };
  }
}

/** Get a plain-English summary of all access states for known tables. */
export async function getSupabaseAccessSummary(): Promise<{
  overallState: SupabaseAccessState;
  tables: Record<string, SupabaseStateResult>;
  userFacing: string;
}> {
  const tables: Record<string, SupabaseStateResult> = {};
  let worstState: SupabaseAccessState = 'available';

  const statePriority: Record<SupabaseAccessState, number> = {
    'available': 0,
    'table-empty': 1,
    'not-used': 2,
    'blocked-by-RLS': 3,
    'blocked-by-auth': 4,
    'not-configured': 5,
  };

  for (const table of SUPABASE_BACKED_TABLES) {
    const result = await getSupabaseAccessState(table);
    tables[table] = result;
    if (statePriority[result.state] > statePriority[worstState]) {
      worstState = result.state;
    }
  }

  const stateMessages: Record<SupabaseAccessState, string> = {
    'available': 'Live Supabase access is working. All backed tables are readable.',
    'blocked-by-auth': 'Supabase is configured but you are not logged in. Log in to access live data.',
    'blocked-by-RLS': 'Supabase is configured and you are logged in, but some tables are blocked by Row Level Security policies.',
    'table-empty': 'Supabase is accessible but some tables have no rows. Static fallback data is shown.',
    'not-used': 'Some sections use local/report data, not Supabase.',
    'not-configured': 'Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.',
  };

  return {
    overallState: worstState,
    tables,
    userFacing: stateMessages[worstState],
  };
}
