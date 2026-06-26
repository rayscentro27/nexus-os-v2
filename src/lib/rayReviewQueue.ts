import { listTable, type Row } from '../services/db';
import type { RayReviewQueueItem } from '../config/rayReviewQueueTypes';

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.trim() ? value : fallback;
}

function arr(value: unknown): string[] {
  return Array.isArray(value) ? value.map((x) => String(x)).filter(Boolean) : [];
}

export function mapTaskRequestToRayReviewItem(row: Row): RayReviewQueueItem {
  const payload = row.payload ?? {};
  const created = text(row.created_at, new Date().toISOString());
  return {
    review_id: text(payload.review_id, text(row.id, crypto.randomUUID())),
    title: text(payload.title, text(row.title, 'Ray review item')),
    decision_type: text(payload.decision_type, 'high_value_strategy_choice') as RayReviewQueueItem['decision_type'],
    department: text(payload.department, 'command_center'),
    source_table: text(payload.source_table, 'task_requests'),
    source_id: text(payload.source_id, text(row.id, '')),
    source_url: text(payload.source_url, '') || null,
    status: text(row.status, text(payload.status, 'pending_review')) as RayReviewQueueItem['status'],
    priority: text(payload.priority, 'medium') as RayReviewQueueItem['priority'],
    risk_level: text(payload.risk_level, 'medium') as RayReviewQueueItem['risk_level'],
    approval_required: Boolean(payload.approval_required ?? row.approval_required),
    ray_decision_required: Boolean(payload.ray_decision_required ?? true),
    due_at: text(payload.due_at, '') || null,
    summary: text(payload.summary, text(row.result_summary, 'Decision summary pending.')),
    hermes_recommendation: text(payload.hermes_recommendation, text(payload.recommendation, 'Hermes should explain options before Ray decides.')),
    options: arr(payload.options),
    pros: arr(payload.pros),
    cons: arr(payload.cons),
    expected_outcome: text(payload.expected_outcome, 'Decision outcome will guide internal prep only until approval gates are satisfied.'),
    risk_notes: arr(payload.risk_notes),
    proof_event_id: text(payload.proof_event_id, '') || null,
    report_path: text(payload.report_path, '') || null,
    created_at: created,
    updated_at: text(row.updated_at, created),
  };
}

export async function loadRayReviewQueue(limit = 50): Promise<RayReviewQueueItem[]> {
  const rows = await listTable('task_requests', { eq: ['task_type', 'ray_review_item'], order: 'created_at', limit });
  return rows.map(mapTaskRequestToRayReviewItem);
}

export function summarizeRayReviewCounts(items: RayReviewQueueItem[]) {
  return {
    total: items.length,
    urgent: items.filter((x) => x.priority === 'urgent').length,
    campaign: items.filter((x) => x.decision_type === 'campaign_publish' || x.decision_type === 'social_post' || x.decision_type === 'email_send').length,
    revenue: items.filter((x) => x.decision_type === 'revenue_decision').length,
    scheduler: items.filter((x) => x.decision_type === 'scheduler_activation').length,
    connector: items.filter((x) => x.decision_type === 'connector_setup').length,
    strategy: items.filter((x) => x.decision_type === 'high_value_strategy_choice' || x.decision_type === 'experiment_selection').length,
  };
}
