import { supabase } from '../lib/supabaseClient';
import type { Approval } from '../types/db';

export async function listApprovals(limit = 25, status?: string): Promise<Approval[]> {
  if (!supabase) return [];
  let q = supabase.from('approvals').select('*').order('created_at', { ascending: false }).limit(limit);
  if (status) q = q.eq('status', status);
  const { data, error } = await q;
  if (error) {
    console.warn('[approvals] listApprovals:', error.message);
    return [];
  }
  return (data ?? []) as Approval[];
}

export async function createApproval(a: Partial<Approval>): Promise<Approval | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.from('approvals').insert(a).select().single();
  if (error) {
    console.warn('[approvals] createApproval:', error.message);
    return null;
  }
  return data as Approval;
}

export async function updateApproval(id: string, status: string, approvedBy?: string): Promise<boolean> {
  if (!supabase) return false;
  const { error } = await supabase
    .from('approvals')
    .update({ status, approved_by: approvedBy ?? null, decided_at: new Date().toISOString() })
    .eq('id', id);
  if (error) {
    console.warn('[approvals] updateApproval:', error.message);
    return false;
  }
  return true;
}
