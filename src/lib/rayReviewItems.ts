/**
 * Nexus OS v2 — Ray Review Live Foundation
 * Prompt 2: Phase F
 *
 * Ray Review item model and management for real approval/revision items.
 * Replaces mock Ray Review data with structured, actionable items.
 */

export type RayReviewType = 'creative' | 'research' | 'client' | 'system' | 'recovery' | 'billing' | 'publishing' | 'trading' | 'grant' | 'credit' | 'app';

export type RayReviewStatus = 'pending' | 'approved' | 'rejected' | 'needs_revision' | 'completed';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface RayReviewItem {
  id: string;
  type: RayReviewType;
  title: string;
  summary: string;
  department: string;
  activation_mode: string;
  risk_level: RiskLevel;
  source_report: string;
  preview_url: string;
  preview_asset: string;
  recommendation: string;
  approve_action: string;
  reject_action: string;
  needs_feedback: boolean;
  status: RayReviewStatus;
  created_at: string;
  updated_at: string;
  feedback?: string;
  revision_notes?: string[];
}

let reviewCounter = 0;

export function generateReviewId(): string {
  reviewCounter++;
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).substring(2, 6);
  return `review_${ts}_${rand}_${reviewCounter}`;
}

export function createRayReviewItem(
  type: RayReviewType,
  title: string,
  summary: string,
  overrides: Partial<RayReviewItem> = {}
): RayReviewItem {
  const now = new Date().toISOString();
  return {
    id: generateReviewId(),
    type,
    title,
    summary,
    department: '',
    activation_mode: 'DRY_RUN',
    risk_level: 'medium',
    source_report: '',
    preview_url: '',
    preview_asset: '',
    recommendation: '',
    approve_action: '',
    reject_action: '',
    needs_feedback: true,
    status: 'pending',
    created_at: now,
    updated_at: now,
    ...overrides,
  };
}

export function approveReviewItem(item: RayReviewItem, feedback?: string): RayReviewItem {
  return {
    ...item,
    status: 'approved',
    feedback,
    updated_at: new Date().toISOString(),
  };
}

export function rejectReviewItem(item: RayReviewItem, feedback: string): RayReviewItem {
  return {
    ...item,
    status: 'rejected',
    feedback,
    updated_at: new Date().toISOString(),
  };
}

export function requestRevision(item: RayReviewItem, notes: string[]): RayReviewItem {
  return {
    ...item,
    status: 'needs_revision',
    revision_notes: notes,
    updated_at: new Date().toISOString(),
  };
}

export function getReviewItemsByStatus(items: RayReviewItem[], status: RayReviewStatus): RayReviewItem[] {
  return items.filter(i => i.status === status);
}

export function getReviewItemsByType(items: RayReviewItem[], type: RayReviewType): RayReviewItem[] {
  return items.filter(i => i.type === type);
}

export function getReviewSummary(items: RayReviewItem[]): {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  needs_revision: number;
  completed: number;
  byType: Record<string, number>;
  byRisk: Record<string, number>;
} {
  const summary = {
    total: items.length,
    pending: 0,
    approved: 0,
    rejected: 0,
    needs_revision: 0,
    completed: 0,
    byType: {} as Record<string, number>,
    byRisk: {} as Record<string, number>,
  };
  for (const item of items) {
    summary[item.status]++;
    summary.byType[item.type] = (summary.byType[item.type] || 0) + 1;
    summary.byRisk[item.risk_level] = (summary.byRisk[item.risk_level] || 0) + 1;
  }
  return summary;
}
