import { supabase } from '../lib/supabaseClient';
import type { AgentJob } from '../types/db';

export async function listJobs(limit = 25, status?: string): Promise<AgentJob[]> {
  if (!supabase) return [];
  let q = supabase.from('agent_jobs').select('*').order('created_at', { ascending: false }).limit(limit);
  if (status) q = q.eq('status', status);
  const { data, error } = await q;
  if (error) {
    console.warn('[jobs] listJobs:', error.message);
    return [];
  }
  return (data ?? []) as AgentJob[];
}

export async function createJob(job: Partial<AgentJob>): Promise<AgentJob | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.from('agent_jobs').insert(job).select().single();
  if (error) {
    console.warn('[jobs] createJob:', error.message);
    return null;
  }
  return data as AgentJob;
}

export async function updateJobStatus(id: string, patch: Partial<AgentJob>): Promise<boolean> {
  if (!supabase) return false;
  const { error } = await supabase
    .from('agent_jobs')
    .update({ ...patch, updated_at: new Date().toISOString() })
    .eq('id', id);
  if (error) {
    console.warn('[jobs] updateJobStatus:', error.message);
    return false;
  }
  return true;
}
