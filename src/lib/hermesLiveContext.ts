/**
 * Hermes Live Context Provider — async live Supabase queries for Hermes chat.
 *
 * This module is called by the chat panel when a Supabase-related question is detected.
 * It queries Supabase tables using the authenticated admin session and returns live context.
 *
 * Falls back to static context when Supabase is unavailable.
 */

import { isSupabaseConfigured, supabase } from './supabaseClient';
import { publicSearch } from './hermesProviders';

export interface LiveHermesResponse {
  text: string;
  source: string;
  sourceType: 'live_supabase' | 'static_fallback' | 'web_search' | 'unavailable';
  liveData: boolean;
  timestamp: string;
  tablesQueried?: string[];
  rowCounts?: Record<string, number>;
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

async function queryTable(table: string, limit = 15): Promise<{ data: unknown[]; error: string | null }> {
  if (!supabase) return { data: [], error: 'Supabase not configured' };
  try {
    const { data, error } = await supabase
      .from(table)
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit);
    if (error) return { data: [], error: error.message };
    return { data: data ?? [], error: null };
  } catch (e) {
    return { data: [], error: String(e) };
  }
}

function summarizeRows(rows: unknown[], label: string): string {
  if (rows.length === 0) return `No ${label} found in Supabase.`;
  const first3 = rows.slice(0, 3).map((r: any) => r.title || r.name || r.component || r.id || 'untitled').join(', ');
  const more = rows.length > 3 ? ` (and ${rows.length - 3} more)` : '';
  return `${rows.length} ${label}: ${first3}${more}`;
}

function valueOf(row: any, keys: string[]): string {
  for (const key of keys) if (row?.[key] !== undefined && row?.[key] !== null) return String(row[key]);
  return '';
}

export function summarizeApprovalRows(taskRows: unknown[], approvalRows: unknown[]): string {
  const allRows = [...taskRows, ...approvalRows] as any[];
  const statusOf = (row: any) => valueOf(row, ['status', 'decision', 'approval_status', 'state']).toLowerCase() || 'unknown';
  const pending = allRows.filter((row) => /pending|queued|review|needs|waiting|hold/.test(statusOf(row)));
  const approved = allRows.filter((row) => /approved|done|completed/.test(statusOf(row)));
  const rejected = allRows.filter((row) => /rejected|declined|blocked/.test(statusOf(row)));
  const held = allRows.filter((row) => /held|hold|paused/.test(statusOf(row)));
  const titles = pending.slice(0, 5).map((row) => valueOf(row, ['title', 'name', 'summary', 'task_title', 'id']) || 'untitled approval');
  const next = titles.length
    ? `The next cards to review are: ${titles.join('; ')}.`
    : 'I do not see pending card titles in the returned rows.';
  return `Live Ray Review summary: ${pending.length} pending/waiting, ${approved.length} approved/done, ${rejected.length} rejected/blocked, and ${held.length} held/paused across ${allRows.length} returned rows.\n\nPlain English: I used the live Supabase/Ray Review path, not the old local zero-card fallback. ${next}\n\nSafe next action: open Ray Review and handle the highest-impact pending card. Any send, charge, publish, trade, deploy, seed, or scheduler change still requires explicit Ray approval.`;
}

/** Build live context for Hermes Supabase queries. */
export async function buildLiveSupabaseContext(message: string): Promise<LiveHermesResponse> {
  const now = new Date().toISOString();
  const lower = message.toLowerCase();

  if (!isSupabaseConfigured) {
    return {
      text: 'Supabase is not configured. VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are not set in the environment.',
      source: 'supabase_unavailable',
      sourceType: 'unavailable',
      liveData: false,
      timestamp: now,
    };
  }

  if (!(await hasSession())) {
    return {
      text: 'Supabase client is configured but there is no authenticated admin session. Please log in to access live data.',
      source: 'supabase_no_session',
      sourceType: 'unavailable',
      liveData: false,
      timestamp: now,
    };
  }

  // Determine what to query based on the question
  const queries: Array<{ table: string; label: string; filter?: { column: string; value: string } }> = [];

  if (/\b(full nexus audit|audit nexus|reality audit|check everything)\b/.test(lower)) {
    queries.push({ table: 'system_health', label: 'system health entries' });
    queries.push({ table: 'nexus_events', label: 'recent Nexus events' });
    queries.push({ table: 'agent_jobs', label: 'agent jobs' });
    queries.push({ table: 'ops_incidents', label: 'operations incidents' });
  }

  if (/\b(approv|ray review|pending|card)\b/.test(lower)) {
    queries.push({ table: 'task_requests', label: 'Ray Review task requests', filter: { column: 'task_type', value: 'ray_review_item' } });
    queries.push({ table: 'approvals', label: 'approvals' });
  }
  if (/\b(research|candidate|source)\b/.test(lower)) {
    queries.push({ table: 'research_sources', label: 'research sources' });
    queries.push({ table: 'research_runs', label: 'research runs' });
  }
  if (/\b(client|customer|profile)\b/.test(lower)) {
    queries.push({ table: 'client_profiles', label: 'client profiles' });
  }
  if (/\b(opportunity|opportunities|business)\b/.test(lower)) {
    queries.push({ table: 'business_opportunities', label: 'business opportunities' });
  }
  if (/\b(offer|monetization|revenue|money)\b/.test(lower)) {
    queries.push({ table: 'monetization_opportunities', label: ' monetization offers' });
  }
  if (/\b(health|system|status)\b/.test(lower)) {
    queries.push({ table: 'system_health', label: 'system health entries' });
  }
  if (/\b(event|activity|journal|log)\b/.test(lower)) {
    queries.push({ table: 'nexus_events', label: 'activity events' });
  }
  if (/\b(what wrote|write proof|written to supabase|seeded|seed execution)\b/.test(lower)) {
    queries.push({ table: 'nexus_events', label: 'Supabase write/activity events' });
    queries.push({ table: 'task_requests', label: 'task requests with persisted receipts' });
  }
  if (/\b(blocker|incident|issue)\b/.test(lower)) {
    queries.push({ table: 'ops_incidents', label: 'ops incidents' });
  }
  if (/\b(table|what tables|see supabase|check supabase|can you see)\b/.test(lower)) {
    // Query a few key tables to show what's accessible
    queries.push({ table: 'approvals', label: 'approvals' });
    queries.push({ table: 'task_requests', label: 'task requests' });
    queries.push({ table: 'nexus_events', label: 'events' });
    queries.push({ table: 'research_sources', label: 'research sources' });
  }
  if (/\b(scheduler|job|automation|loop)\b/.test(lower)) {
    queries.push({ table: 'agent_jobs', label: 'agent jobs' });
  }

  // Default: query approvals and events if no specific match
  if (queries.length === 0) {
    queries.push({ table: 'approvals', label: 'approvals' });
    queries.push({ table: 'task_requests', label: 'task requests' });
  }

  const results: Record<string, unknown[]> = {};
  const tableNames: string[] = [];
  const rowCounts: Record<string, number> = {};
  let hasError = false;
  let errorMsg = '';
  let successfulQueries = 0;

  for (const q of queries) {
    const base = q.filter ? { data: [] as unknown[], error: null } : await queryTable(q.table);
    let rows: unknown[];
    if (q.filter && supabase) {
      const { data: filtered, error: filterErr } = await supabase
        .from(q.table)
        .select('*')
        .eq(q.filter.column, q.filter.value)
        .order('created_at', { ascending: false })
        .limit(15);
      rows = filterErr ? [] : (filtered ?? []);
      if (filterErr) { hasError = true; errorMsg = filterErr.message; }
      else successfulQueries += 1;
    } else {
      rows = base.data;
      if (base.error) { hasError = true; errorMsg = base.error; }
      else successfulQueries += 1;
    }
    results[q.table] = rows;
    tableNames.push(q.table);
    rowCounts[q.table] = rows.length;
  }

  // Build response text
  let responseText = '';
  const parts: string[] = [];

  for (const q of queries) {
    const rows = results[q.table] || [];
    parts.push(summarizeRows(rows, q.label));
  }

  if (/\b(approv|ray review|pending|card)\b/.test(lower)) {
    responseText = `${summarizeApprovalRows(results.task_requests || [], results.approvals || [])}\n\nLive Supabase context:\n\n${parts.join('\n\n')}`;
  } else {
    responseText = `Live Supabase context:\n\n${parts.join('\n\n')}`;
  }

  if (hasError) {
    responseText += `\n\nNote: Some queries returned errors: ${errorMsg.slice(0, 100)}`;
  }

  responseText += successfulQueries > 0
    ? `\n\nSource: Live Supabase (authenticated session, RLS-applied). Data is read-only. Any resulting execution remains approval-gated.`
    : `\n\nNo Supabase query succeeded, so this response does not claim live data access.`;

  return {
    text: responseText,
    source: successfulQueries > 0 ? 'live_supabase_context' : 'supabase_query_failed',
    sourceType: successfulQueries > 0 ? 'live_supabase' : 'unavailable',
    liveData: successfulQueries > 0,
    timestamp: now,
    tablesQueried: tableNames,
    rowCounts,
  };
}

/** Build context for "can you search the internet" type questions. */
export async function buildWebSearchResponse(query: string): Promise<LiveHermesResponse> {
  const now = new Date().toISOString();

  // Check if search is enabled via env var
  const searchEnabled = (import.meta.env.VITE_HERMES_SEARCH_ENABLED as string | undefined) === 'true';

  if (!searchEnabled) {
    return {
      text: 'I cannot search the internet from this layer yet. The web search endpoint (hermes-search edge function) is not enabled. To activate it, set VITE_HERMES_SEARCH_ENABLED=true and configure a search API key (Brave, Tavily, or SerpAPI) in Supabase Edge Function secrets.\n\nI can create a research task for you to investigate this topic through the safe internal research pipeline.',
      source: 'web_search_unavailable',
      sourceType: 'unavailable',
      liveData: false,
      timestamp: now,
    };
  }

  try {
    const result = await publicSearch(query);
    if (!result.configured) {
      return {
        text: 'Web search is enabled but the search provider is not configured. Set a search API key (Brave, Tavily, or SerpAPI) in Supabase Edge Function secrets.',
        source: 'web_search_not_configured',
        sourceType: 'unavailable',
        liveData: false,
        timestamp: now,
      };
    }
    if (result.blocked) {
      return {
        text: result.text,
        source: 'web_search_blocked',
        sourceType: 'unavailable',
        liveData: false,
        timestamp: now,
      };
    }
    return {
      text: `Web search results:\n\n${result.text}\n\nSource: Live web search via configured provider. Results are public information only.`,
      source: 'live_web_search',
      sourceType: 'web_search',
      liveData: true,
      timestamp: now,
    };
  } catch (e) {
    return {
      text: `Web search failed: ${String(e).slice(0, 100)}.\n\nI can create a research task for you to investigate this topic through the safe internal research pipeline.`,
      source: 'web_search_error',
      sourceType: 'unavailable',
      liveData: false,
      timestamp: now,
    };
  }
}
