import { supabase } from '../lib/supabaseClient';

export type Row = Record<string, any>;

/** Generic read for any table the admin can SELECT. Empty array when unconfigured/blocked. */
export async function listTable(
  table: string,
  opts: { limit?: number; order?: string; ascending?: boolean; eq?: [string, string] } = {},
): Promise<Row[]> {
  if (!supabase) return [];
  let q = supabase.from(table).select('*').limit(opts.limit ?? 50);
  q = q.order(opts.order ?? 'created_at', { ascending: opts.ascending ?? false });
  if (opts.eq) q = q.eq(opts.eq[0], opts.eq[1]);
  const { data, error } = await q;
  if (error) { console.warn(`[db] ${table}:`, error.message); return []; }
  return (data ?? []) as Row[];
}

export async function countRows(table: string): Promise<number> {
  if (!supabase) return 0;
  const { count, error } = await supabase.from(table).select('*', { count: 'exact', head: true });
  if (error) return 0;
  return count ?? 0;
}
