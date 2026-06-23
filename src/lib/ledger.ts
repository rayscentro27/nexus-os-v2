import { supabase } from './supabaseClient';

/**
 * Ledger writes — every meaningful UI action records to Supabase (the source of truth).
 * Uses the authenticated admin session (anon key + signed-in admin). Admin INSERT/UPDATE
 * policies (migration 0003) gate these; non-admins get an RLS error, surfaced to the UI.
 * No external side effects here — these only write rows.
 */

export async function createEvent(evt: {
  lane: string; action: string; status?: string; title?: string;
  summary?: string; source?: string; severity?: string; payload?: Record<string, unknown>;
  job_id?: string | null; approval_id?: string | null;
}): Promise<string | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.from('nexus_events').insert({
    status: 'info', source: 'nexus_os_ui', ...evt,
  }).select('id').single();
  if (error) { console.warn('[ledger] createEvent:', error.message); return null; }
  return data?.id ?? null;
}

export async function createJob(job: {
  lane: string; job_type: string; status?: string; input?: Record<string, unknown>;
}): Promise<string | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.from('agent_jobs').insert({
    status: 'stubbed', ...job,
  }).select('id').single();
  if (error) { console.warn('[ledger] createJob:', error.message); return null; }
  return data?.id ?? null;
}

export async function decideApproval(
  id: string, status: 'approved' | 'rejected' | 'revise', email?: string,
): Promise<boolean> {
  if (!supabase) return false;
  const { error } = await supabase.from('approvals').update({
    status, approved_by: email ?? null, decided_at: new Date().toISOString(),
  }).eq('id', id);
  if (error) { console.warn('[ledger] decideApproval:', error.message); return false; }
  return true;
}
