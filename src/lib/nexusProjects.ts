import { supabase } from './supabaseClient';
import { listTable, type Row } from '../services/db';
import type {
  NexusDepartment,
  NexusEnrichmentSource,
  NexusEnrichmentStatus,
  NexusProject,
  NexusProjectEnrichment,
  NexusProjectStatus,
} from '../config/nexusProjectTypes';

const nowIso = () => new Date().toISOString();

function text(value: unknown, fallback = ''): string {
  if (value == null) return fallback;
  if (typeof value === 'string') return value || fallback;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  return fallback;
}

function arr(value: unknown): string[] {
  return Array.isArray(value) ? value.map((x) => text(x)).filter(Boolean) : [];
}

function score(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function scoreLabel(value: number | null): string {
  if (value == null) return 'unscored';
  if (value >= 75) return 'high';
  if (value >= 50) return 'medium';
  if (value >= 30) return 'low';
  return 'very low';
}

function obj(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function statusFrom(value: unknown): NexusProjectStatus {
  const s = text(value).toLowerCase();
  if (s.includes('block') || s.includes('fail')) return 'blocked';
  if (s.includes('paper') || s.includes('demo')) return 'paper_demo';
  if (s.includes('backtest')) return 'backtested';
  if (s.includes('proposed')) return 'proposed';
  if (s.includes('reject')) return 'rejected';
  if (s.includes('park') || s.includes('skip')) return 'parked';
  if (s.includes('done') || s.includes('complete') || s.includes('success') || s.includes('published')) return 'done';
  if (s.includes('implement') || s.includes('running') || s.includes('progress') || s.includes('claimed')) return 'implementing';
  if (s.includes('sched')) return 'scheduled';
  if (s.includes('approve')) return 'approved';
  if (s.includes('review') || s.includes('pending') || s.includes('revise')) return 'needs_review';
  if (s.includes('score') || s.includes('reviewed')) return 'scored';
  if (s.includes('summar')) return 'summarized';
  return 'researching';
}

function statusFromEnrichment(value: unknown): NexusProjectStatus {
  const s = text(value).toLowerCase();
  if (s === 'failed') return 'blocked';
  if (s === 'needs_review') return 'needs_review';
  if (s === 'scored') return 'scored';
  if (s === 'enriched') return 'summarized';
  if (s.startsWith('pending')) return 'researching';
  return statusFrom(s);
}

function normalizeEnrichment(input: unknown): Partial<NexusProjectEnrichment> {
  const e = obj(input);
  return {
    enrichment_status: text(e.enrichment_status) as NexusEnrichmentStatus || undefined,
    summary: text(e.summary),
    score: score(e.score),
    score_label: text(e.score_label),
    category: text(e.category),
    destination: text(e.destination),
    pros: arr(e.pros),
    cons: arr(e.cons),
    recommendation: text(e.recommendation),
    proposed_schedule: text(e.proposed_schedule),
    next_action: text(e.next_action),
    confidence: score(e.confidence),
    risk_triggers: arr(e.risk_triggers),
    approval_required: typeof e.approval_required === 'boolean' ? e.approval_required : undefined,
    hermes_memory_summary: text(e.hermes_memory_summary),
    source_summary: text(e.source_summary),
    enrichment_source: text(e.enrichment_source) as NexusEnrichmentSource || undefined,
    enriched_at: text(e.enriched_at) || null,
    reviewed_at: text(e.reviewed_at) || null,
    proof_event_id: text(e.proof_event_id) || null,
  };
}

function deterministicEnrichment(row: Row): Partial<NexusProjectEnrichment> {
  const m = obj(row.metadata);
  const p = obj(row.payload);
  const category = text(row.category ?? m.primary_category ?? p.category, 'uncategorized');
  const destination = text(m.recommended_destination ?? p.destination ?? row.destination, 'Source Intake & Review');
  const s = score(m.total_opportunity_score ?? p.score ?? row.score ?? row.overall_score);
  const risk = arr(m.risk_triggers ?? m.reasons_against ?? row.claim_flags ?? p.risk_triggers);
  const pending = text(m.enrichment_status ?? m.transcript_status).includes('pending');
  const summary = text(row.core_idea ?? row.summary ?? row.source_summary ?? row.description ?? row.snippet, pending ? 'Saved metadata is available. Transcript/NotebookLM enrichment is pending.' : '');
  return {
    enrichment_status: text(m.enrichment_status, pending ? 'pending_transcript' : (s != null ? 'scored' : 'metadata_saved')) as NexusEnrichmentStatus,
    summary,
    score: s,
    score_label: scoreLabel(s),
    category,
    destination,
    pros: [
      category !== 'uncategorized' ? `Category signal: ${category}.` : '',
      destination ? `Recommended destination: ${destination}.` : '',
    ].filter(Boolean),
    cons: [
      s != null && s < 30 ? `Low deterministic score (${s}/100).` : '',
      risk.length ? `Risk flags: ${risk.join(', ')}.` : '',
      pending ? 'Transcript/NotebookLM enrichment is still pending.' : '',
    ].filter(Boolean),
    recommendation: text(row.recommended_action ?? m.recommendation ?? m.recommended_action, risk.length ? 'Ray should review the risk flags before routing.' : 'Review with Hermes, then route safely or park.'),
    proposed_schedule: text(m.proposed_schedule, 'Review now; schedule automation only after approval.'),
    next_action: text(m.next_action, risk.length ? 'Send to Approvals or request Ray review.' : 'Choose the next safe internal action.'),
    confidence: score(row.confidence ?? obj(m.scores).confidence ?? p.confidence),
    risk_triggers: risk,
    approval_required: Boolean(m.ray_decision_needed ?? p.approval_required ?? risk.length),
    hermes_memory_summary: text(m.hermes_memory_summary, `${text(row.title, 'Saved source')}: ${category} -> ${destination}; score=${s ?? 'unscored'}.`),
    source_summary: text(row.snippet ?? row.why_it_matters ?? p.snippet, summary),
    enrichment_source: 'fallback',
    enriched_at: text(m.enriched_at) || null,
    reviewed_at: text(m.reviewed_at) || null,
    proof_event_id: text(m.proof_event_id ?? p.proof_event_id) || null,
  };
}

function mergeEnrichment(...parts: Array<Partial<NexusProjectEnrichment> | undefined>): Partial<NexusProjectEnrichment> {
  const out: Partial<NexusProjectEnrichment> = {};
  for (const part of parts) {
    if (!part) continue;
    for (const [key, value] of Object.entries(part) as Array<[keyof NexusProjectEnrichment, unknown]>) {
      if (Array.isArray(value)) {
        if (value.length) (out as Record<string, unknown>)[key] = value;
      } else if (value !== undefined && value !== null && value !== '') {
        (out as Record<string, unknown>)[key] = value;
      }
    }
  }
  return out;
}

function base(row: Row, patch: Partial<NexusProject>): NexusProject {
  const created = text(row.created_at, nowIso());
  const fallback = deterministicEnrichment(row);
  const enriched = mergeEnrichment(
    fallback,
    normalizeEnrichment(row.payload?.project_enrichment),
    normalizeEnrichment(row.metadata?.project_enrichment),
    patch as Partial<NexusProjectEnrichment>,
  );
  const projectScore = patch.score ?? enriched.score ?? score(row.score ?? row.overall_score);
  const enrichmentStatus = (patch.enrichment_status ?? enriched.enrichment_status ?? 'metadata_saved') as NexusEnrichmentStatus;
  return {
    project_id: text(patch.project_id, text(row.id, crypto.randomUUID())),
    title: text(patch.title, text(row.title, 'Untitled project')),
    department: patch.department ?? 'source_intake',
    owner_tab: text(patch.owner_tab, 'intake'),
    project_type: text(patch.project_type, 'project'),
    status: patch.status ?? statusFromEnrichment(enrichmentStatus) ?? statusFrom(row.status ?? row.decision ?? row.review_status),
    score: projectScore,
    score_label: text(patch.score_label, text(enriched.score_label, scoreLabel(projectScore))),
    priority: patch.priority ?? 'medium',
    enrichment_status: enrichmentStatus,
    enrichment_source: (patch.enrichment_source ?? enriched.enrichment_source ?? 'fallback') as NexusEnrichmentSource,
    confidence: patch.confidence ?? enriched.confidence ?? null,
    summary: text(patch.summary, text(enriched.summary, text(row.summary ?? row.source_summary ?? row.description ?? row.snippet, ''))),
    pros: patch.pros ?? (enriched.pros?.length ? enriched.pros : arr(row.pros ?? row.metadata?.pros)),
    cons: patch.cons ?? (enriched.cons?.length ? enriched.cons : arr(row.cons ?? row.metadata?.cons)),
    recommendation: text(patch.recommendation, text(enriched.recommendation, text(row.recommendation ?? row.recommended_action ?? row.smallest_test ?? row.diagnosis, 'Review the saved metadata and choose the next safe action.'))),
    proposed_changes: patch.proposed_changes ?? arr(row.proposed_changes ?? row.metadata?.proposed_changes ?? row.revision_notes),
    proposed_schedule: text(patch.proposed_schedule, text(enriched.proposed_schedule, text(row.proposed_schedule ?? row.metadata?.proposed_schedule, getProjectScheduleLabel({ status: statusFrom(row.status ?? row.decision) } as NexusProject)))),
    next_action: text(patch.next_action, text(enriched.next_action, text(row.next_action ?? row.recommended_fix ?? row.smallest_test ?? row.recommended_action, 'Review with Hermes.'))),
    hermes_memory_summary: text(patch.hermes_memory_summary, text(enriched.hermes_memory_summary, '')),
    category: text(patch.category, text(enriched.category, text(row.category ?? row.metadata?.primary_category, ''))),
    destination: text(patch.destination, text(enriched.destination, text(row.destination ?? row.metadata?.recommended_destination, ''))),
    approval_required: patch.approval_required ?? enriched.approval_required ?? Boolean(row.approval_required ?? row.payload?.approval_required ?? row.metadata?.approval_required),
    feedback_requested: patch.feedback_requested ?? /review|revise|pending/i.test(text(row.status ?? row.decision)),
    risk_triggers: patch.risk_triggers ?? (enriched.risk_triggers?.length ? enriched.risk_triggers : arr(row.risk_triggers ?? row.payload?.risk_flags ?? row.metadata?.risk_triggers ?? row.claim_flags)),
    visual_url: patch.visual_url ?? (text(row.visual_url ?? row.preview_url ?? row.asset_ref ?? row.payload?.image_url, '') || null),
    source_url: patch.source_url ?? (text(row.source_url ?? row.url ?? row.page_url ?? row.payload?.source_url, '') || null),
    source_title: patch.source_title ?? (text(row.source_title ?? row.source_name ?? row.title, '') || null),
    data_sources: patch.data_sources ?? [],
    related_process_id: patch.related_process_id ?? (text(row.process_id ?? row.worker_key ?? row.job_type, '') || null),
    related_task_request_id: patch.related_task_request_id ?? (text(row.task_request_id ?? row.payload?.task_request_id, '') || null),
    related_approval_id: patch.related_approval_id ?? (text(row.approval_id ?? row.payload?.approval_id, '') || null),
    proof_event_id: patch.proof_event_id ?? enriched.proof_event_id ?? (text(row.proof_event_id ?? row.event_id, '') || null),
    enriched_at: patch.enriched_at ?? enriched.enriched_at ?? null,
    reviewed_at: patch.reviewed_at ?? enriched.reviewed_at ?? null,
    created_at: text(patch.created_at, created),
    updated_at: text(patch.updated_at, text(row.updated_at ?? row.completed_at ?? row.resolved_at, created)),
    raw: row,
  };
}

export function getProjectDepartment(project: Pick<NexusProject, 'department'>): NexusDepartment {
  return project.department;
}

export function getProjectReviewState(project: Pick<NexusProject, 'approval_required' | 'feedback_requested' | 'status'>): string {
  if (project.approval_required) return 'Approval required';
  if (project.feedback_requested || project.status === 'needs_review') return 'Needs review';
  if (project.status === 'blocked') return 'Blocked';
  return 'Ready for safe internal action';
}

export function getProjectScheduleLabel(project: Pick<NexusProject, 'status'>): string {
  if (project.status === 'scheduled') return 'Scheduled by existing process metadata.';
  if (project.status === 'implementing') return 'In progress now; review next run output.';
  if (project.status === 'blocked') return 'Blocked until Ray decides or missing connection is fixed.';
  return 'No schedule set. Hermes should propose a low-risk next step.';
}

export function getProjectHermesRecommendation(project: NexusProject): string {
  if (project.summary.trim()) return project.recommendation || 'Review the summary, risks, and next action before routing.';
  return 'I can review the saved metadata now. Summary/enrichment is pending.';
}

export function mapResearchSourceToProject(row: Row, review?: Row, task?: Row): NexusProject {
  const m = row.metadata ?? {};
  const enrichment = mergeEnrichment(
    deterministicEnrichment(row),
    normalizeEnrichment(task?.payload?.project_enrichment),
    normalizeEnrichment(row.metadata?.project_enrichment),
    normalizeEnrichment(review?.metadata?.project_enrichment),
    review ? deterministicEnrichment(review) : undefined,
  );
  const reviewStatus = text(m.review_status, text(row.review_status, 'saved'));
  return base(row, {
    project_id: `research:${row.id}`,
    title: text(row.title ?? row.url, 'Saved source'),
    department: 'source_intake',
    owner_tab: 'intake',
    project_type: text(row.source_type, 'research_source'),
    status: statusFromEnrichment(enrichment.enrichment_status) ?? (score(m.total_opportunity_score) != null ? 'scored' : statusFrom(reviewStatus)),
    enrichment_status: enrichment.enrichment_status,
    enrichment_source: enrichment.enrichment_source,
    score: enrichment.score ?? score(m.total_opportunity_score ?? row.score),
    score_label: enrichment.score_label,
    confidence: enrichment.confidence,
    summary: text(enrichment.summary, text(row.snippet, '')),
    pros: enrichment.pros,
    cons: enrichment.cons,
    recommendation: text(enrichment.recommendation, text(m.recommended_action ?? m.recommended_destination, 'Saved. Summary/enrichment pending.')),
    proposed_schedule: text(enrichment.proposed_schedule, text(m.proposed_schedule, 'Saved immediately; enrichment can run later.')),
    next_action: text(enrichment.next_action, text(m.next_action, 'Review metadata or request safe enrichment.')),
    hermes_memory_summary: enrichment.hermes_memory_summary,
    category: enrichment.category,
    destination: enrichment.destination,
    approval_required: enrichment.approval_required,
    risk_triggers: enrichment.risk_triggers,
    proof_event_id: enrichment.proof_event_id,
    enriched_at: enrichment.enriched_at,
    reviewed_at: enrichment.reviewed_at,
    source_url: text(row.url, '') || null,
    source_title: text(row.title, '') || null,
    related_task_request_id: text(task?.id, '') || null,
    data_sources: ['research_sources', 'transcript_reviews', 'intake_events'],
  });
}

export function mapCreativeAssetToProject(row: Row): NexusProject {
  return base(row, {
    project_id: `creative:${row.id}`,
    title: text(row.title ?? row.asset_type, 'Creative asset'),
    department: 'creative_studio',
    owner_tab: 'creative',
    project_type: text(row.asset_type, 'creative_asset'),
    status: statusFrom(row.status),
    score: score(row.score),
    summary: text(row.body ?? row.content ?? row.hook, ''),
    recommendation: text(row.cta ?? row.payload?.recommendation, 'Review draft quality and compliance before approval.'),
    visual_url: text(row.payload?.image_url ?? row.payload?.preview_url, '') || null,
    data_sources: ['creative_assets', 'creative_scores', 'publish_readiness_packages'],
  });
}

export function mapTaskRequestToProject(row: Row): NexusProject {
  const enrichment = mergeEnrichment(deterministicEnrichment(row), normalizeEnrichment(row.payload?.project_enrichment));
  return base(row, {
    project_id: `task:${row.id}`,
    title: text(row.payload?.title ?? row.payload?.strategy_name ?? row.payload?.source_title ?? row.summary ?? row.task_type, 'Task request'),
    department: getDepartmentFromTab(text(row.payload?.owner_tab ?? row.payload?.target_tab ?? row.payload?.department, 'agent_jobs')),
    owner_tab: text(row.payload?.owner_tab ?? row.payload?.target_tab, 'jobs'),
    project_type: text(row.task_type, 'task_request'),
    status: statusFrom(row.payload?.capture_status ?? row.status),
    enrichment_status: enrichment.enrichment_status,
    score: enrichment.score,
    summary: text(enrichment.summary, text(row.summary ?? row.result_summary, '')),
    pros: enrichment.pros?.length ? enrichment.pros : arr(row.payload?.pros),
    cons: enrichment.cons?.length ? enrichment.cons : arr(row.payload?.cons),
    recommendation: text(enrichment.recommendation, text(row.payload?.recommendation, 'Review this safe request before assigning worker time.')),
    proposed_schedule: text(enrichment.proposed_schedule, text(row.payload?.proposed_schedule, 'Manual review only.')),
    next_action: text(enrichment.next_action, text(row.payload?.next_action, 'Review this department card.')),
    approval_required: enrichment.approval_required ?? Boolean(row.payload?.approval_required),
    risk_triggers: enrichment.risk_triggers?.length ? enrichment.risk_triggers : arr(row.payload?.risk_triggers ?? (row.payload?.review_trigger ? [row.payload.review_trigger] : [])),
    visual_url: text(row.payload?.visual_url, '') || null,
    source_url: text(row.payload?.source_url, '') || null,
    source_title: text(row.payload?.source_title, '') || null,
    related_task_request_id: text(row.id),
    proof_event_id: text(row.payload?.proof_event_id, '') || null,
    data_sources: ['task_requests'],
  });
}

export function mapApprovalToProject(row: Row): NexusProject {
  return base(row, {
    project_id: `approval:${row.id}`,
    title: text(row.title ?? row.item_type, 'Approval item'),
    department: 'approvals',
    owner_tab: 'approvals',
    project_type: text(row.item_type, 'approval'),
    status: statusFrom(row.status),
    summary: text(row.summary, ''),
    recommendation: 'Ray should approve, reject, or request changes in the Approvals tab. Hermes can advise only.',
    approval_required: true,
    related_approval_id: text(row.id),
    related_task_request_id: text(row.payload?.task_request_id, '') || null,
    data_sources: ['approvals'],
  });
}

export function mapProcessRegistryItemToProject(row: Row): NexusProject {
  return base(row, {
    project_id: `job:${row.id}`,
    title: text(row.job_type ?? row.name, 'Automation job'),
    department: 'agent_jobs',
    owner_tab: 'jobs',
    project_type: text(row.job_type ?? row.agent_class, 'agent_job'),
    status: statusFrom(row.status),
    summary: text(row.output?.summary ?? row.error ?? row.last_error, ''),
    recommendation: row.status === 'failed' ? 'Review the error and create a safe diagnostic task.' : 'Review the latest output and proof event before rerunning.',
    proposed_schedule: 'Manual or approved future schedule only.',
    next_action: row.status === 'queued' ? 'Run the approved manual runner when ready.' : 'Review proof/output.',
    related_process_id: text(row.job_type, '') || null,
    data_sources: ['agent_jobs', 'agent_registry'],
  });
}

export function mapSeoOpportunityToProject(row: Row): NexusProject {
  return base(row, {
    project_id: `seo:${row.id}`,
    title: text(row.title, 'Growth opportunity'),
    department: 'growth',
    owner_tab: 'seo',
    project_type: text(row.opportunity_type, 'seo_opportunity'),
    status: statusFrom(row.status),
    score: score(row.score),
    summary: text(row.reason, ''),
    recommendation: text(row.recommended_action, 'Create a draft/report only until growth automation is connected.'),
    source_url: text(row.page_url, '') || null,
    data_sources: ['seo_opportunities', 'seo_sites'],
  });
}

export function mapImprovementToProject(row: Row): NexusProject {
  return base(row, {
    project_id: `ops:${row.id}`,
    title: text(row.title, 'Improvement candidate'),
    department: 'ops_improvements',
    owner_tab: 'ops',
    project_type: text(row.capability_area ?? row.source_type, 'improvement_candidate'),
    status: statusFrom(row.decision ?? row.status),
    score: score(row.capability_gain ?? row.urgency),
    summary: text(row.summary, ''),
    recommendation: 'Prefer a small implementation task or more research; deploys and local commands remain gated.',
    source_url: text(row.source_url, '') || null,
    data_sources: ['improvement_candidates', 'ops_incidents', 'nexus_events'],
  });
}

export function mapOpportunityToProject(row: Row): NexusProject {
  return base(row, {
    project_id: `opportunity:${row.id}`,
    title: text(row.title, 'Opportunity'),
    department: 'opportunity_lab',
    owner_tab: 'opportunities',
    project_type: 'monetization_opportunity',
    status: statusFrom(row.decision ?? row.status),
    score: score(row.overall_score),
    summary: text(row.source_summary ?? row.money_angle, ''),
    pros: [
      row.speed_to_cash != null ? `Speed to cash: ${row.speed_to_cash}/10` : '',
      row.recurring_revenue_potential != null ? `Recurring potential: ${row.recurring_revenue_potential}/10` : '',
    ].filter(Boolean),
    cons: [
      row.compliance_risk != null ? `Compliance risk: ${row.compliance_risk}/10` : '',
      row.implementation_effort != null ? `Implementation effort: ${row.implementation_effort}/10` : '',
    ].filter(Boolean),
    recommendation: text(row.smallest_test, 'Define the smallest low/no-cost test.'),
    next_action: text(row.smallest_test, 'Create a test task or park it.'),
    data_sources: ['monetization_opportunities'],
  });
}

function getDepartmentFromTab(tab: string): NexusDepartment {
  if (tab === 'intake') return 'source_intake';
  if (tab === 'opportunity_lab') return 'opportunity_lab';
  if (tab === 'opportunities') return 'opportunity_lab';
  if (tab === 'goclear') return 'opportunity_lab';
  if (tab === 'design') return 'design_library';
  if (tab === 'creative') return 'creative_studio';
  if (tab === 'seo') return 'growth';
  if (tab === 'ops') return 'ops_improvements';
  if (tab === 'jobs') return 'agent_jobs';
  if (tab === 'command') return 'command_center';
  if (tab === 'approvals') return 'approvals';
  if (tab === 'events') return 'events_feed';
  if (tab === 'integrations') return 'integrations';
  if (tab === 'trading') return 'trading_lab';
  return 'agent_jobs';
}

function taskBelongsToTab(row: Row, tabId: string, taskTypes: string[] = []): boolean {
  const payload = row.payload ?? {};
  return taskTypes.includes(String(row.task_type))
    || payload.owner_tab === tabId
    || payload.target_tab === tabId
    || payload.department === getDepartmentFromTab(tabId);
}

export async function loadDepartmentProjects(tabId: string): Promise<NexusProject[]> {
  if (tabId === 'intake') {
    const [sources, reviews, tasks] = await Promise.all([
      listTable('research_sources', { order: 'created_at', limit: 40 }),
      listTable('transcript_reviews', { order: 'created_at', limit: 80 }),
      listTable('task_requests', { order: 'created_at', limit: 20 }),
    ]);
    const reviewBySourceId = new Map<string, Row>();
    const reviewByUrl = new Map<string, Row>();
    const reviewByTitle = new Map<string, Row>();
    for (const review of reviews) {
      const meta = review.metadata ?? {};
      if (meta.research_source_id) reviewBySourceId.set(String(meta.research_source_id), review);
      if (meta.source_url) reviewByUrl.set(String(meta.source_url), review);
      if (review.title) reviewByTitle.set(String(review.title).toLowerCase(), review);
    }
    const taskBySourceId = new Map<string, Row>();
    const taskByUrl = new Map<string, Row>();
    for (const task of tasks) {
      if (task.payload?.research_source_id) taskBySourceId.set(String(task.payload.research_source_id), task);
      if (task.payload?.source_url) taskByUrl.set(String(task.payload.source_url), task);
    }
    return [
      ...sources.map((source) => mapResearchSourceToProject(
        source,
        reviewBySourceId.get(String(source.id)) ?? reviewByUrl.get(String(source.url)) ?? reviewByTitle.get(String(source.title ?? '').toLowerCase()),
        taskBySourceId.get(String(source.id)) ?? taskByUrl.get(String(source.url)),
      )),
      ...tasks.map(mapTaskRequestToProject).filter((p) => p.project_type.includes('source')),
    ]
      .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  }
  if (tabId === 'opportunities') {
    const [opportunities, tasks] = await Promise.all([
      listTable('monetization_opportunities', { order: 'created_at', limit: 40 }),
      listTable('task_requests', { order: 'created_at', limit: 40 }),
    ]);
    return [
      ...opportunities.map(mapOpportunityToProject),
      ...tasks
        .filter((t) => t.task_type === 'opportunity_lab_project' || t.payload?.owner_tab === 'opportunities' || t.payload?.department === 'opportunity_lab')
        .map(mapTaskRequestToProject),
    ].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  }
  if (tabId === 'goclear') {
    const tasks = await listTable('task_requests', { order: 'created_at', limit: 50 });
    return tasks
      .filter((t) => taskBelongsToTab(t, 'goclear', ['goclear_revenue_metric_project']))
      .map(mapTaskRequestToProject)
      .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  }
  if (tabId === 'creative') {
    const [assets, tasks] = await Promise.all([
      listTable('creative_assets', { order: 'created_at', limit: 40 }),
      listTable('task_requests', { order: 'created_at', limit: 40 }),
    ]);
    return [
      ...assets.map(mapCreativeAssetToProject),
      ...tasks.filter((t) => taskBelongsToTab(t, 'creative', ['creative_studio_project'])).map(mapTaskRequestToProject),
    ].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  }
  if (tabId === 'seo') {
    const [seoRows, tasks] = await Promise.all([
      listTable('seo_opportunities', { order: 'created_at', limit: 40 }),
      listTable('task_requests', { order: 'created_at', limit: 40 }),
    ]);
    return [
      ...seoRows.map(mapSeoOpportunityToProject),
      ...tasks.filter((t) => taskBelongsToTab(t, 'seo', ['seo_marketing_project'])).map(mapTaskRequestToProject),
    ].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  }
  if (tabId === 'ops') return (await listTable('improvement_candidates', { order: 'created_at', limit: 40 })).map(mapImprovementToProject);
  if (tabId === 'jobs') {
    const [jobs, tasks] = await Promise.all([
      listTable('agent_jobs', { order: 'created_at', limit: 40 }),
      listTable('task_requests', { order: 'created_at', limit: 60 }),
    ]);
    return [
      ...jobs.map(mapProcessRegistryItemToProject),
      ...tasks.filter((t) => taskBelongsToTab(t, 'jobs', ['agent_job_project'])).map(mapTaskRequestToProject),
    ].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  }
  if (tabId === 'design') {
    const [sources, packets, reviews, tasks] = await Promise.all([
      listTable('design_inspiration_sources', { order: 'created_at', limit: 20 }),
      listTable('feature_design_packets', { order: 'created_at', limit: 20 }),
      listTable('ui_quality_reviews', { order: 'created_at', limit: 20 }),
      listTable('task_requests', { order: 'created_at', limit: 40 }),
    ]);
    return [
      ...sources.map((r) => base(r, {
        project_id: `design-source:${r.id}`, title: text(r.source_name, 'Design source'),
        department: 'design_library', owner_tab: 'design', project_type: text(r.category, 'design_inspiration'),
        status: 'summarized', score: score(r.usefulness_score), summary: text(r.summary, ''),
        recommendation: 'Use as reference only; do not clone external assets.', data_sources: ['design_inspiration_sources'],
      })),
      ...packets.map((r) => base(r, {
        project_id: `design-packet:${r.id}`, title: text(r.feature_name, 'Feature design packet'),
        department: 'design_library', owner_tab: 'design', project_type: 'feature_design_packet',
        status: statusFrom(r.status), summary: text(r.user_goal, ''), data_sources: ['feature_design_packets'],
      })),
      ...reviews.map((r) => base(r, {
        project_id: `design-review:${r.id}`, title: text(r.review_title, 'UI quality review'),
        department: 'design_library', owner_tab: 'design', project_type: 'ui_quality_review',
        status: 'scored', score: score(r.overall_score), summary: text(r.recommendation, ''),
        data_sources: ['ui_quality_reviews'],
      })),
      ...tasks.filter((t) => taskBelongsToTab(t, 'design', ['design_library_project'])).map(mapTaskRequestToProject),
    ].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  }
  if (tabId === 'command') return (await listTable('task_requests', { order: 'created_at', limit: 40 }))
    .filter((t) => taskBelongsToTab(t, 'command', ['command_center_summary']))
    .map(mapTaskRequestToProject);
  if (tabId === 'approvals') {
    const [approvals, tasks] = await Promise.all([
      listTable('approvals', { order: 'created_at', limit: 40 }),
      listTable('task_requests', { order: 'created_at', limit: 40 }),
    ]);
    return [
      ...approvals.map(mapApprovalToProject),
      ...tasks.filter((t) => taskBelongsToTab(t, 'approvals', ['approval_decision_project'])).map(mapTaskRequestToProject),
    ].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  }
  if (tabId === 'events') return (await listTable('task_requests', { order: 'created_at', limit: 40 }))
    .filter((t) => taskBelongsToTab(t, 'events', ['event_ledger_project']))
    .map(mapTaskRequestToProject);
  if (tabId === 'integrations') return (await listTable('task_requests', { order: 'created_at', limit: 40 }))
    .filter((t) => taskBelongsToTab(t, 'integrations', ['integration_status_project']))
    .map(mapTaskRequestToProject);
  if (tabId === 'trading') {
    const [strategies, tasks] = await Promise.all([
      listTable('trading_strategy_candidates', { order: 'created_at', limit: 40 }),
      listTable('task_requests', { order: 'created_at', limit: 40 }),
    ]);
    return [
      ...strategies.map((r) => base(r, {
        project_id: `trading-strategy:${r.id}`,
        title: text(r.title ?? r.strategy_name ?? r.name, 'Trading strategy candidate'),
        department: 'trading_lab',
        owner_tab: 'trading',
        project_type: 'paper_strategy_research',
        status: statusFrom(r.status),
        score: score(r.score ?? r.total_score),
        summary: text(r.summary ?? r.thesis ?? r.description, ''),
        recommendation: 'Research/backtest only. Live trading and broker execution are blocked.',
        next_action: 'Review strategy notes and request bounded backtest/report only.',
        approval_required: false,
        risk_triggers: ['live_trading_blocked'],
        data_sources: ['trading_strategy_candidates'],
      })),
      ...tasks.filter((t) => taskBelongsToTab(t, 'trading', [
        'trading_lab_research_project',
        'trading_lab_backtest_import',
      ])).map(mapTaskRequestToProject),
    ].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at));
  }
  return [];
}

export async function saveInstantResearchSource(input: {
  source_type: string;
  source_url?: string | null;
  title?: string | null;
  snippet?: string | null;
  target_use?: string;
  priority?: string;
  tags?: string[];
  requested_by?: string | null;
}): Promise<{ id: string | null; error: string | null }> {
  if (!supabase) return { id: null, error: 'Supabase is not configured.' };
  const { data, error } = await supabase.from('research_sources').insert({
    source_type: input.source_type,
    title: input.title || input.source_url || 'Saved research source',
    url: input.source_url || null,
    snippet: input.snippet || null,
    why_it_matters: input.target_use || null,
    metadata: {
      review_status: 'saved',
      transcript_status: input.source_url ? 'enrichment_pending' : 'not_required',
      enrichment_status: input.source_url ? 'pending_transcript' : 'metadata_saved',
      project_enrichment: deterministicEnrichment({
        title: input.title || input.source_url || 'Saved research source',
        url: input.source_url || null,
        snippet: input.snippet || 'Saved metadata is available. Transcript/NotebookLM enrichment is pending.',
        why_it_matters: input.target_use || null,
        metadata: {
          transcript_status: input.source_url ? 'enrichment_pending' : 'not_required',
          enrichment_status: input.source_url ? 'pending_transcript' : 'metadata_saved',
          recommended_destination: input.target_use || 'Auto-route (by score)',
          tags: input.tags || [],
        },
      }),
      recommended_destination: input.target_use || 'Auto-route (by score)',
      priority: input.priority || 'Medium',
      tags: input.tags || [],
      requested_by: input.requested_by || 'operator',
      instant_research_mode: true,
      enrichment_pending: true,
    },
  }).select('id').single();
  if (error) return { id: null, error: error.message.replace(/Bearer\s+[A-Za-z0-9._-]+/g, 'Bearer [redacted]').slice(0, 180) };
  return { id: data?.id ?? null, error: null };
}
