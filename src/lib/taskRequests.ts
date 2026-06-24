/**
 * task_requests writer — creates a Ray-APPROVED structured task request. Hermes never executes it;
 * an assigned worker (internal/private for sensitive scopes) picks it up and returns redacted
 * status/summary. Uses the admin session + admin RLS (migration 0011). No side effects beyond the row.
 */

import { supabase } from './supabaseClient';
import type { ProposedTask } from './hermesIntent';

/**
 * Compact, redacted latest-task status for the model's dynamic context. Selects ONLY safe
 * columns (task_type, sensitivity, status, result_summary) — never payload/forbidden_data of a
 * sensitive task. Returns '' when none or unconfigured.
 */
export async function latestStatusForPrompt(): Promise<string> {
  if (!supabase) return '';
  const { data, error } = await supabase
    .from('task_requests')
    .select('task_type,sensitivity,status,result_summary')
    .order('created_at', { ascending: false })
    .limit(1);
  if (error || !data || data.length === 0) return '';
  const t = data[0];
  const summary = t.result_summary ? ` — ${String(t.result_summary).slice(0, 160)}` : '';
  return `${t.task_type} · ${t.sensitivity} · ${t.status}${summary}`.slice(0, 240);
}

export async function createTaskRequest(task: ProposedTask, email: string | null): Promise<string | null> {
  if (!supabase) return null;
  const { data, error } = await supabase.from('task_requests').insert({
    task_type: task.task_type,
    requested_by: 'hermes',
    approved_by_ray: email ?? 'ray',
    sensitivity: task.sensitivity,
    allowed_data_scope: task.allowed_data_scope,
    forbidden_data: task.forbidden_data,
    assigned_worker_type: task.assigned_worker_type,
    hermes_visibility: task.hermes_visibility,
    status: 'requested',
    payload: task.payload,
  }).select('id').single();
  if (error) { console.warn('[taskRequests] create:', error.message); return null; }
  return data?.id ?? null;
}
