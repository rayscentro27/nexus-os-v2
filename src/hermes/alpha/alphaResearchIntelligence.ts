/** Phase J: bounded, evidence-first Alpha research intelligence.
 *
 * This module is deliberately transport-neutral. Nexus owns persistence,
 * evidence ingestion, provider choice, and authority. Alpha only plans,
 * analyzes accepted evidence, and returns advisory artifacts.
 */

export const ALPHA_RESEARCH_TYPES = [
  "MARKET_RESEARCH", "COMPETITOR_RESEARCH", "BUSINESS_OPPORTUNITY_RESEARCH",
  "AFFILIATE_RESEARCH", "FUNDING_PROGRAM_RESEARCH", "GRANT_RESEARCH", "SEO_RESEARCH",
  "PRODUCT_SERVICE_RESEARCH", "PRICING_RESEARCH", "TECHNOLOGY_RESEARCH",
  "OPEN_SOURCE_RESEARCH", "INDUSTRY_TREND_RESEARCH", "CONTENT_RESEARCH", "TRADING_RESEARCH",
] as const;
export type AlphaResearchType = typeof ALPHA_RESEARCH_TYPES[number];
export type AlphaResearchStatus = "COMPLETE" | "PARTIAL" | "INSUFFICIENT_EVIDENCE" | "BLOCKED" | "FAILED";
export type EvidenceDisposition = "DIRECT_EVIDENCE" | "DERIVED_ANALYSIS" | "INFERENCE" | "UNKNOWN";
export type Confidence = "HIGH" | "MEDIUM" | "LOW" | "UNSUPPORTED";
export type SourceQuality = "PRIMARY" | "AUTHORITATIVE" | "HIGH_QUALITY_SECONDARY" | "SECONDARY" | "COMMUNITY" | "UNVERIFIED";
export type FreshnessStatus = "CURRENT" | "AGING" | "STALE" | "UNKNOWN";

export interface ResearchLimits { maxSources: number; maxEvidenceJobs: number; maxModelCalls: number; maxRuntimeMs: number; maxOutputChars: number; }
export interface AlphaResearchJob {
  schema_version: "nexus.alpha-research-job.v1";
  research_job_id: string; objective: string; research_type: AlphaResearchType;
  business_context: Record<string, unknown>; scope: Record<string, unknown>;
  constraints: Record<string, unknown>; source_policy: { allowed: string[]; public_only: boolean; evidence_required: boolean };
  freshness_requirement: string; limits: ResearchLimits; cost_budget: { currency: "USD"; max_model_calls: number; max_remote_jobs: number };
  requested_by: string; tenant_context: { scope: string; tenant_id: string | null }; created_at: string;
}
export interface ResearchPlan { objective: string; key_questions: string[]; source_classes: string[]; freshness_requirement: string; search_strategy: string; stopping_criteria: string[]; evidence_gaps: string[]; limits: ResearchLimits; }
export interface EvidenceRef {
  evidence_id: string; artifact_ref: string; original_source: string; source_type: string;
  retrieved_at: string; published_at?: string; material_hash?: string; quality: SourceQuality;
  freshness: FreshnessStatus; status: "ACCEPTED" | "DUPLICATE" | "REJECTED";
}
export interface AlphaClaim { claim: string; claim_type: EvidenceDisposition; confidence: Confidence; evidence_refs: string[]; source_count: number; source_quality: SourceQuality[]; freshness: FreshnessStatus; contradictions: string[]; notes: string[]; }
export interface OpportunityCandidate { opportunity_title: string; description: string; evidence: string[]; potential_value: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"; effort: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"; risk: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"; business_fit: "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN"; confidence: Confidence; next_research_needed: string[]; output_type: "RESEARCH_OPPORTUNITY_CANDIDATE"; }
export interface ResearchPack { schema_version: "nexus.alpha-research-pack.v1"; research_job_id: string; objective: string; status: AlphaResearchStatus; executive_summary: string; findings: string[]; claims: AlphaClaim[]; opportunities: OpportunityCandidate[]; risks: string[]; unknowns: string[]; contradictions: string[]; sources: EvidenceRef[]; evidence_refs: string[]; freshness: { requirement: string; status: FreshnessStatus; completed_at: string }; cost_usage: { model_calls: number; evidence_jobs: number; source_count: number; runtime_ms: number; cost_status: "KNOWN" | "ESTIMATED" | "UNKNOWN"; estimated_cost_usd?: number }; created_at: string; }
export interface ResearchReceipt { schema_version: "nexus.alpha-research-receipt.v1"; receipt_id: string; research_job_id: string; objective: string; status: AlphaResearchStatus; started_at: string; completed_at: string; source_count: number; evidence_count: number; model_usage: { calls: number; provider: string; tokens: "KNOWN" | "UNKNOWN" }; remote_worker_usage: { jobs: number; capability: "evidence_ingestion.crawl4ai" | "none"; cost: "KNOWN" | "UNKNOWN" }; research_pack_ref: string; report_ref: string; opportunity_candidate_count: number; error_classification?: string; }

export interface AcceptedEvidence { evidence_id: string; artifact_ref: string; original_source: string; source_type: string; retrieved_at: string; published_at?: string; material_hash?: string; text: string; quality?: SourceQuality; status?: "ACCEPTED" | "DUPLICATE"; }
export interface ResearchExecution { plan: ResearchPlan; pack: ResearchPack; report: string; receipt: ResearchReceipt; }

const PII = /\b(?:ssn|social security|credit report|bank account|routing number|client vault|private client|password|api[_ -]?key|secret|credential|private communication)\b|\b\d{3}-\d{2}-\d{4}\b/i;
const now = () => new Date().toISOString();
const id = (prefix: string) => `${prefix}-${Math.random().toString(16).slice(2, 14)}`;

export function validateResearchJob(input: Partial<AlphaResearchJob>): AlphaResearchJob {
  if (!input.objective?.trim()) throw new Error("objective_required");
  if (PII.test(`${input.objective} ${JSON.stringify(input.business_context || {})} ${JSON.stringify(input.scope || {})}`)) throw new Error("SAFETY_BLOCKED: sensitive client or credential context");
  if (!input.research_type || !ALPHA_RESEARCH_TYPES.includes(input.research_type)) throw new Error("invalid_research_type");
  const supplied = input.limits || {} as ResearchLimits;
  const limits: ResearchLimits = { maxSources: supplied.maxSources ?? 10, maxEvidenceJobs: supplied.maxEvidenceJobs ?? 3, maxModelCalls: supplied.maxModelCalls ?? 4, maxRuntimeMs: supplied.maxRuntimeMs ?? 120_000, maxOutputChars: supplied.maxOutputChars ?? 40_000 };
  if (Object.values(limits).some((value) => !Number.isInteger(value) || value <= 0)) throw new Error("limits_must_be_positive_integers");
  if (limits.maxSources > 50 || limits.maxEvidenceJobs > 10 || limits.maxModelCalls > 20 || limits.maxRuntimeMs > 900_000 || limits.maxOutputChars > 200_000) throw new Error("limits_exceed_policy");
  return { schema_version: "nexus.alpha-research-job.v1", research_job_id: input.research_job_id || id("alpha-job"), objective: input.objective.trim(), research_type: input.research_type, business_context: input.business_context || {}, scope: input.scope || {}, constraints: input.constraints || { advisory_only: true, no_external_action: true }, source_policy: input.source_policy || { allowed: ["canonical_evidence", "public_search", "youtube_transcript", "markitdown", "crawl4ai"], public_only: true, evidence_required: true }, freshness_requirement: input.freshness_requirement || "CURRENT", limits, cost_budget: input.cost_budget || { currency: "USD", max_model_calls: limits.maxModelCalls, max_remote_jobs: limits.maxEvidenceJobs }, requested_by: input.requested_by || "founder_admin", tenant_context: input.tenant_context || { scope: "founder_admin", tenant_id: null }, created_at: input.created_at || now() };
}

export function createResearchPlan(job: AlphaResearchJob): ResearchPlan {
  const questions = ["What is directly supported by current public evidence?", "What is likely analysis versus unknown?", "What contradictions or freshness limits affect the conclusion?"];
  if (job.research_type === "COMPETITOR_RESEARCH") questions.push("How do public offer, pricing, audience, positioning, proof, and structure compare?");
  if (job.research_type === "TECHNOLOGY_RESEARCH" || job.research_type === "OPEN_SOURCE_RESEARCH") questions.push("What capability, license, maintenance, security, and integration tradeoffs are evidenced?");
  return { objective: job.objective, key_questions: questions, source_classes: ["official product/program pages", "authoritative documentation", "public secondary analysis"], freshness_requirement: job.freshness_requirement, search_strategy: "Use existing search first; request one bounded Nexus evidence-ingestion job only when browser-backed acquisition adds value.", stopping_criteria: [`${job.limits.maxSources} useful sources reached`, `${job.limits.maxEvidenceJobs} evidence jobs reached`, "key questions answered or gap cannot be safely resolved", "runtime or output budget reached"], evidence_gaps: [], limits: job.limits };
}

function freshness(retrieved: string, requirement: string): FreshnessStatus { const age = Date.now() - Date.parse(retrieved); if (!Number.isFinite(age)) return "UNKNOWN"; const days = age / 86400000; if (/hour|day|current|today/i.test(requirement)) return days <= 7 ? "CURRENT" : days <= 30 ? "AGING" : "STALE"; return days <= 30 ? "CURRENT" : days <= 180 ? "AGING" : "STALE"; }
function qualityOf(e: AcceptedEvidence): SourceQuality { return e.quality || (/\.gov\b|\.edu\b|official|documentation/i.test(e.original_source) ? "AUTHORITATIVE" : "UNVERIFIED"); }
export function preserveContradictions(claims: AlphaClaim[]): string[] {
  const contradictions: string[] = [];
  for (let i = 0; i < claims.length; i += 1) for (let j = i + 1; j < claims.length; j += 1) {
    const left = claims[i].claim.toLowerCase(); const right = claims[j].claim.toLowerCase();
    if ((/not\b|unsupported|unavailable|no /.test(left) && /available|supported|yes /.test(right)) || (/not\b|unsupported|unavailable|no /.test(right) && /available|supported|yes /.test(left))) contradictions.push(`Conflicting source claims preserved: ${claims[i].evidence_refs[0]} vs ${claims[j].evidence_refs[0]}`);
  }
  return contradictions;
}
export function buildOpportunityCandidate(job: AlphaResearchJob, refs: EvidenceRef[]): OpportunityCandidate | null {
  if (!["BUSINESS_OPPORTUNITY_RESEARCH", "AFFILIATE_RESEARCH", "FUNDING_PROGRAM_RESEARCH", "GRANT_RESEARCH"].includes(job.research_type)) return null;
  return { opportunity_title: `Research candidate: ${job.objective.slice(0, 100)}`, description: "Evidence-backed candidate for later governed review; no application, signup, publishing, payment, or execution is authorized.", evidence: refs.map((ref) => ref.evidence_id), potential_value: "UNKNOWN", effort: "UNKNOWN", risk: "UNKNOWN", business_fit: "UNKNOWN", confidence: refs.length ? "LOW" : "UNSUPPORTED", next_research_needed: ["Verify eligibility, terms, freshness, and business fit from primary sources."], output_type: "RESEARCH_OPPORTUNITY_CANDIDATE" };
}
function report(pack: ResearchPack): string { return [`# Alpha Research Report`, `## Objective\n${pack.objective}`, `## Executive Summary\n${pack.executive_summary}`, `## Key Findings\n${pack.findings.map((x) => `- ${x}`).join("\n") || "- No supported findings."}`, `## Evidence\n${pack.claims.map((c) => `- **${c.confidence} / ${c.claim_type}:** ${c.claim} (evidence: ${c.evidence_refs.join(", ") || "none"})`).join("\n") || "- No claims accepted."}`, `## Opportunities\n${pack.opportunities.map((x) => `- ${x.opportunity_title} — advisory research candidate only`).join("\n") || "- None identified."}`, `## Risks and Unknowns\n${[...pack.risks, ...pack.unknowns].map((x) => `- ${x}`).join("\n") || "- None recorded."}`, `## Contradictions\n${pack.contradictions.map((x) => `- ${x}`).join("\n") || "- None recorded."}`, `## Research Limits\nEvidence-first, public-only, bounded execution. Recommendations are advisory and require Nexus/Ray review.`].join("\n\n"); }

export function executeAlphaResearch(jobInput: Partial<AlphaResearchJob>, evidence: AcceptedEvidence[], options: { provider?: string; remoteJobs?: number; startedAt?: string } = {}): ResearchExecution {
  const job = validateResearchJob(jobInput); const started = options.startedAt || now(); const plan = createResearchPlan(job); const selected = evidence.slice(0, job.limits.maxSources).filter((e) => e.status !== "DUPLICATE");
  const refs = selected.map((e): EvidenceRef => ({ evidence_id: e.evidence_id, artifact_ref: e.artifact_ref, original_source: e.original_source, source_type: e.source_type, retrieved_at: e.retrieved_at, published_at: e.published_at, material_hash: e.material_hash, quality: qualityOf(e), freshness: freshness(e.retrieved_at, job.freshness_requirement), status: "ACCEPTED" }));
  const claims: AlphaClaim[] = selected.map((e) => ({ claim: e.text.replace(/\s+/g, " ").trim().slice(0, 500), claim_type: "DIRECT_EVIDENCE", confidence: e.text.trim() ? "MEDIUM" : "UNSUPPORTED", evidence_refs: [e.evidence_id], source_count: 1, source_quality: [qualityOf(e)], freshness: freshness(e.retrieved_at, job.freshness_requirement), contradictions: [], notes: [] }));
  const unknowns = selected.length ? ["Independent corroboration and non-public commercial terms remain unknown unless separately evidenced."] : ["No accepted evidence was supplied."];
  const contradictions = preserveContradictions(claims); const candidate = buildOpportunityCandidate(job, refs);
  const status: AlphaResearchStatus = selected.length === 0 ? "INSUFFICIENT_EVIDENCE" : selected.length < Math.min(2, job.limits.maxSources) ? "PARTIAL" : "COMPLETE";
  const completed = now(); const pack: ResearchPack = { schema_version: "nexus.alpha-research-pack.v1", research_job_id: job.research_job_id, objective: job.objective, status, executive_summary: selected.length ? `Alpha analyzed ${selected.length} accepted public evidence artifact(s). Findings are advisory and traceable to canonical evidence.` : "Alpha could not produce a supported conclusion because no accepted evidence was available.", findings: claims.map((c) => c.claim), claims, opportunities: candidate ? [candidate] : [], risks: ["Public claims may reflect commercial bias; verify before any decision."], unknowns, contradictions, sources: refs, evidence_refs: refs.map((r) => r.evidence_id), freshness: { requirement: job.freshness_requirement, status: refs.some((r) => r.freshness === "STALE") ? "STALE" : refs.length ? "CURRENT" : "UNKNOWN", completed_at: completed }, cost_usage: { model_calls: 0, evidence_jobs: Math.min(options.remoteJobs || 0, job.limits.maxEvidenceJobs), source_count: selected.length, runtime_ms: Math.max(0, Date.parse(completed) - Date.parse(started)), cost_status: "UNKNOWN" }, created_at: completed };
  const rendered = report(pack).slice(0, job.limits.maxOutputChars); const receipt: ResearchReceipt = { schema_version: "nexus.alpha-research-receipt.v1", receipt_id: id("alpha-receipt"), research_job_id: job.research_job_id, objective: job.objective, status, started_at: started, completed_at: completed, source_count: selected.length, evidence_count: refs.length, model_usage: { calls: 0, provider: options.provider || "none", tokens: "UNKNOWN" }, remote_worker_usage: { jobs: pack.cost_usage.evidence_jobs, capability: pack.cost_usage.evidence_jobs ? "evidence_ingestion.crawl4ai" : "none", cost: "UNKNOWN" }, research_pack_ref: `research-packs/${job.research_job_id}.json`, report_ref: `research-reports/${job.research_job_id}.md`, opportunity_candidate_count: pack.opportunities.length };
  return { plan, pack, report: rendered, receipt };
}

export function validateEvidenceForClaim(claim: AlphaClaim): boolean { return claim.confidence === "UNSUPPORTED" || claim.evidence_refs.length > 0; }
export function detectSensitiveResearchPayload(value: unknown): boolean { return PII.test(JSON.stringify(value)); }
