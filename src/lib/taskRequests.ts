/**
 * task_requests writer — creates a Ray-APPROVED structured task request. Hermes never executes it;
 * an assigned worker (internal/private for sensitive scopes) picks it up and returns redacted
 * status/summary. Uses the admin session + admin RLS (migration 0011). No side effects beyond the row.
 */

import { supabase } from './supabaseClient';
import type { ProposedTask } from './hermesIntent';

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
