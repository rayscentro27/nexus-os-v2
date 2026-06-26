import type { HermesDecisionMemory, HermesRecommendationHistory } from '../config/hermesDecisionMemory';

const nowIso = () => new Date().toISOString();

export function createHermesDecisionMemory(input: Partial<HermesDecisionMemory> & { title: string; summary: string }): HermesDecisionMemory {
  const now = nowIso();
  return {
    memory_id: input.memory_id ?? crypto.randomUUID(),
    kind: input.kind ?? 'ray_feedback',
    title: input.title,
    summary: input.summary,
    source_type: input.source_type ?? 'ray_feedback',
    source_id: input.source_id ?? null,
    department: input.department ?? null,
    confidence: input.confidence ?? 0.75,
    weight: input.weight ?? 1,
    safe_visibility: 'internal_summary',
    created_at: input.created_at ?? now,
    updated_at: input.updated_at ?? now,
  };
}

export function createHermesRecommendationHistory(
  input: Partial<HermesRecommendationHistory> & { recommendation: string; rationale: string },
): HermesRecommendationHistory {
  const now = nowIso();
  return {
    recommendation_id: input.recommendation_id ?? crypto.randomUUID(),
    report_id: input.report_id ?? null,
    project_id: input.project_id ?? null,
    recommendation: input.recommendation,
    rationale: input.rationale,
    decision: input.decision ?? 'pending',
    outcome_summary: input.outcome_summary ?? null,
    created_at: input.created_at ?? now,
    updated_at: input.updated_at ?? now,
  };
}
