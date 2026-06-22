import { supabase } from '../lib/supabaseClient';
import type { SystemHealth } from '../types/db';

/** Returns the latest health row per component (most recent created_at wins). */
export async function listSystemHealth(): Promise<SystemHealth[]> {
  if (!supabase) return [];
  const { data, error } = await supabase
    .from('system_health')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(100);
  if (error) {
    console.warn('[health] listSystemHealth:', error.message);
    return [];
  }
  const latest = new Map<string, SystemHealth>();
  for (const row of (data ?? []) as SystemHealth[]) {
    if (!latest.has(row.component)) latest.set(row.component, row);
  }
  return [...latest.values()];
}
