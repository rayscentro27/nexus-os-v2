import { supabase } from '../lib/supabaseClient';
import type { NexusEvent } from '../types/db';

/**
 * Event ledger access. Reads use the shared (anon) client. Writes from the browser require
 * RLS write policies (not enabled Day 1) — production writes happen server/script side with
 * the service role. These helpers exist so both contexts share one contract.
 */

export async function listRecentEvents(limit = 25, lane?: string): Promise<NexusEvent[]> {
  if (!supabase) return [];
  let q = supabase.from('nexus_events').select('*').order('created_at', { ascending: false }).limit(limit);
  if (lane) q = q.eq('lane', lane);
  const { data, error } = await q;
  if (error) {
    console.warn('[events] listRecentEvents:', error.message);
    return [];
  }
  return (data ?? []) as NexusEvent[];
}

export async function createEvent(evt: Partial<NexusEvent>): Promise<NexusEvent | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.from('nexus_events').insert(evt).select().single();
  if (error) {
    console.warn('[events] createEvent:', error.message);
    return null;
  }
  return data as NexusEvent;
}
