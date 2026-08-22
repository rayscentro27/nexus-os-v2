import type { NexusProject } from '../config/nexusProjectTypes';
import type { GoClearRevenueMetric, GoClearMetricKey, GoClearTruthClass } from '../config/goclearRevenueMetrics';
import { GOCLEAR_REVENUE_METRIC_DEFINITIONS } from '../config/goclearRevenueMetrics';

export function estimateGoClearRevenuePotential(project: Pick<NexusProject, 'score' | 'project_type' | 'summary' | 'recommendation'>): number {
  const score = project.score ?? 40;
  const blob = `${project.project_type} ${project.summary} ${project.recommendation}`.toLowerCase();
  let base = 97;
  if (blob.includes('upgrade') || blob.includes('concierge')) base = 297;
  if (blob.includes('affiliate') || blob.includes('partner') || blob.includes('nav')) base += 150;
  if (blob.includes('seo') || blob.includes('lead')) base += 97;
  return Math.round(base * Math.max(0.25, Math.min(1.5, score / 70)));
}

export function buildGoClearMetric(
  metric_key: GoClearMetricKey,
  value: number | null,
  source_department: string,
  updated_at: string,
  proof_event_id?: string | null,
  truth_class: GoClearTruthClass = 'UNKNOWN',
  source_status: GoClearRevenueMetric['source_status'] = 'NOT_CONNECTED',
): GoClearRevenueMetric {
  const def = GOCLEAR_REVENUE_METRIC_DEFINITIONS[metric_key];
  return {
    metric_key,
    label: def.label,
    value,
    unit: def.unit,
    conversion_stage: def.defaultStage,
    estimated_revenue_potential: metric_key === 'estimated_revenue_potential' ? value : null,
    actual_revenue: metric_key === 'actual_revenue' && truth_class === 'ACTUAL' ? value : null,
    truth_class,
    source_status,
    proof_event_id: proof_event_id ?? null,
    source_department,
    updated_at,
  };
}

export function summarizeGoClearRevenueMetrics(metrics: GoClearRevenueMetric[]): string {
  if (!metrics.length) return 'No live revenue metrics connected yet.';
  const estimated = metrics.filter(m => m.truth_class === 'OPPORTUNITY_ESTIMATE' || m.metric_key === 'estimated_revenue_potential').reduce((sum, m) => sum + (m.estimated_revenue_potential ?? 0), 0);
  const actual = metrics.filter(m => m.truth_class === 'ACTUAL').reduce((sum, m) => sum + (m.actual_revenue ?? 0), 0);
  const actualLabel = metrics.some(m => m.truth_class === 'ACTUAL') ? `$${actual}` : 'UNKNOWN / NOT_CONNECTED';
  return `GoClear Revenue Hub has ${metrics.length} metric signals, opportunity estimate $${estimated}, actual revenue ${actualLabel}.`;
}
