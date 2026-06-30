/**
 * Hermes Supabase Context Adapter — stub for live Supabase queries.
 *
 * Currently: NO live Supabase access from this chat layer.
 * Future: anon-safe read-only queries when wired.
 */

export interface SupabaseContextResult {
  liveSupabaseAvailable: false;
  reason: string;
  queried: boolean;
  table: string | null;
  data: unknown[] | null;
}

const NOT_AVAILABLE: SupabaseContextResult = {
  liveSupabaseAvailable: false,
  reason: 'No server-side Hermes Supabase context endpoint is wired yet. This chat layer uses local bundled context only.',
  queried: false,
  table: null,
  data: null,
};

/** Attempt to query Supabase for context. Returns honest stub for now. */
export function querySupabaseContext(table: string, _filter?: string): SupabaseContextResult {
  // Future: if anon-safe Supabase query is available, use it here.
  return { ...NOT_AVAILABLE, table };
}

/** Check if Supabase is available for Hermes context. */
export function isSupabaseAvailable(): boolean {
  return false;
}

/** Get an honest status message about Supabase availability. */
export function getSupabaseStatusMessage(): string {
  return 'I do not have live Supabase access from this chat layer yet. I can see loaded page context and local bundled data, but I cannot query Supabase directly. If you need live data, I can create a task to query it through a safe internal process.';
}
