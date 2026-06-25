/** Universal request/queue/approval-visibility helper. Every tab uses this to file safe work or
 *  review-required work consistently — so we stop splitting task_requests vs approvals per tab.
 *
 *  Model (NEXUS_APPROVAL_VISIBILITY_MODEL.md): the request always goes to `task_requests` (the
 *  owning-tab queue). If policy says approval is required, a LINKED `approvals` row is also created
 *  (status pending) so it shows in the Approvals tab. Safe queue items never create an approval and
 *  never clutter Approvals. Never marks anything approved; never weakens gates. */
import { createTaskRequest } from './taskRequests';
import { createEvent, createApproval } from './ledger';
import { classifyCaptureSubmission } from '../config/nexusActionPolicy';

export interface SourceSubmission {
  source_type: string; source_url?: string | null; title?: string | null; snippet?: string | null;
  target_use?: string; priority?: string; tags?: string[];
  capture_command_preview?: string | null;
}

export interface SubmitResult {
  ok: boolean; taskRequestId: string | null; approvalId: string | null;
  approvalRequired: boolean; triggers: string[]; statusLabel: string; message: string;
}

/** File a source-capture submission per the universal policy. Safe → Capture Queue only;
 *  review-required → Capture Queue + linked Approvals row. Writes a nexus_events proof. */
export async function submitSourceCapture(sub: SourceSubmission, email: string | null): Promise<SubmitResult> {
  const payload = {
    action_type: sub.source_type === 'youtube_video' ? 'youtube_capture_request' : 'source_capture_request',
    source_type: sub.source_type, source_url: sub.source_url ?? null, title: sub.title ?? null,
    snippet: sub.snippet ? sub.snippet.slice(0, 500) : null, target_use: sub.target_use ?? 'Auto-route (by score)',
    priority: sub.priority ?? 'Medium', tags: sub.tags ?? [], requested_by: email ?? 'operator',
    requested_by_admin: true, created_at: new Date().toISOString(),
    capture_command_preview: sub.capture_command_preview ?? null,
    source_capture_policy: 'safe_admin_submitted_capture_v1',
    external_ai: false, scheduler: false, v1_jobs_touched: false,
    note: 'Browser capture is disabled. A worker runs the CLI wrapper after the item is queued/approved.',
  };
  const cls = classifyCaptureSubmission(payload);
  const taskType = payload.action_type;

  const taskRequestId = await createTaskRequest({
    task_type: taskType, sensitivity: 'internal_summary',
    allowed_data_scope: ['public', 'internal_summary'], forbidden_data: ['customer_private', 'secrets'],
    assigned_worker_type: 'research_worker', hermes_visibility: 'summary',
    payload: { ...payload, approval_required: cls.approvalRequired, review_trigger: cls.triggers[0] ?? null,
               capture_status: cls.approvalRequired ? 'needs_review' : 'queued' },
    summary: cls.approvalRequired
      ? `Source needs Ray review (${cls.triggers[0]}): ${(sub.title || sub.source_url || sub.source_type)?.toString().slice(0, 60)}`
      : `Safe Capture Queue: ${(sub.title || sub.source_url || sub.source_type)?.toString().slice(0, 60)} — runs via CLI wrapper, no approval needed`,
  }, email);

  let approvalId: string | null = null;
  if (taskRequestId && cls.approvalRequired) {
    approvalId = await createApproval({
      lane: 'research', item_type: cls.itemType ?? 'source_capture_review',
      title: `Review source: ${(sub.title || sub.source_url || sub.source_type)?.toString().slice(0, 60)}`,
      summary: `Reason: ${cls.triggers.join(', ')}. Requested action: capture + route. task_request ${taskRequestId}.`,
      payload: { task_request_id: taskRequestId, source_url: sub.source_url, source_type: sub.source_type,
                 review_trigger: cls.triggers[0] ?? null, requested_action: 'capture_and_route', created_at: new Date().toISOString() },
    });
  }

  if (taskRequestId) {
    await createEvent({
      lane: 'research', action: cls.approvalRequired ? 'source_capture_review_requested' : 'source_capture_queued',
      status: 'pending', title: (sub.title || sub.source_url || sub.source_type)?.toString().slice(0, 80),
      summary: `${taskType} ${taskRequestId}${approvalId ? ` · approval ${approvalId}` : ''} · approval_required=${cls.approvalRequired}`,
      payload: { task_request_id: taskRequestId, approval_id: approvalId, source_url: sub.source_url, browser_capture: false, review_trigger: cls.triggers[0] ?? null },
    });
  }

  return {
    ok: !!taskRequestId, taskRequestId, approvalId, approvalRequired: cls.approvalRequired,
    triggers: cls.triggers, statusLabel: cls.statusLabel,
    message: !taskRequestId ? 'Could not file request (check sign-in / RLS).'
      : cls.approvalRequired
        ? `Filed for Ray review — appears in Approvals (reason: ${cls.triggers[0]}). task_request ${taskRequestId.slice(0, 8)}…`
        : `Queued for safe capture — Ray approval is only required if Nexus cannot categorize the source or if the next action is risky. (queue id ${taskRequestId.slice(0, 8)}…)`,
  };
}
