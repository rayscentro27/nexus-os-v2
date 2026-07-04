import { readFileSync, writeFileSync, readdirSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const ROOT = dirname(dirname(dirname(__filename)));
const FIXTURES_DIR = join(ROOT, "nexus_research", "internal_test_runner", "fixtures");
const RESULTS_DIR = join(ROOT, "nexus_research", "internal_test_runner", "results");
const REPORTS_DIR = join(ROOT, "reports", "nexus_research", "internal_test_runner");

const APPROVED_CATEGORIES = ["manual_notes", "credit_utilization", "business_setup"] as const;

export interface GoClearTestProfile {
  profile_id: string;
  profile_type: "hypothetical";
  profile_label: string;
  credit_utilization_pct: number;
  has_business_entity: boolean;
  entity_type: string;
  time_in_business_months: number;
  annual_revenue: number;
  existing_debt: number;
  credit_score_range: string;
  funding_goal: string;
  has_business_bank_account: boolean;
  has_business_website: boolean;
  has_business_email: boolean;
  has_business_phone: boolean;
  notes: string;
}

export interface ReadinessScorecardDraft {
  credit_utilization_readiness: "low" | "medium" | "high";
  business_setup_readiness: "low" | "medium" | "high";
  funding_readiness_preparation: "low" | "medium" | "high";
  documentation_readiness: "low" | "medium" | "high";
  client_education_need: "low" | "medium" | "high";
  ray_review_priority: "low" | "medium" | "high";
}

export interface AdminReadinessNote {
  profile_id: string;
  profile_label: string;
  credit_utilization_notes: string;
  business_setup_notes: string;
  missing_information: string[];
  internal_recommendation: string;
  risk_compliance_cautions: string[];
  blocked_actions: string[];
  ray_review_required: true;
  generated_at: string;
  output_label: string;
}

export interface RayReviewDraftForProfile {
  title: string;
  profile_summary: string;
  recommended_next_step: string;
  why_it_matters: string;
  what_ray_should_approve_reject: string;
  what_must_not_be_client_facing_yet: string[];
  blocked_guarantees: string[];
  client_facing_allowed: "no";
  approval_required: true;
  generated_at: string;
  output_label: string;
}

export interface InternalTestResult {
  profile_id: string;
  profile_label: string;
  admin_readiness_note: AdminReadinessNote;
  ray_review_draft: RayReviewDraftForProfile;
  readiness_scorecard: ReadinessScorecardDraft;
}

export interface InternalTestManifest {
  generated_at: string;
  total_profiles: number;
  categories_used: string[];
  profiles: Array<{
    profile_id: string;
    profile_label: string;
    ray_review_priority: string;
  }>;
  output_label: string;
}

function loadProfile(filename: string): GoClearTestProfile {
  const raw = readFileSync(join(FIXTURES_DIR, filename), "utf-8");
  const jsonStr = raw.replace(/^HYPOTHETICAL INTERNAL TEST PROFILE.*\n\n/, "");
  return JSON.parse(jsonStr);
}

function scoreUtilization(pct: number): "low" | "medium" | "high" {
  if (pct <= 30) return "high";
  if (pct <= 55) return "medium";
  return "low";
}

function scoreBusinessSetup(profile: GoClearTestProfile): "low" | "medium" | "high" {
  let score = 0;
  if (profile.has_business_entity) score++;
  if (profile.has_business_bank_account) score++;
  if (profile.has_business_website) score++;
  if (profile.has_business_email) score++;
  if (profile.has_business_phone) score++;
  if (profile.time_in_business_months >= 6) score++;
  if (score >= 5) return "high";
  if (score >= 3) return "medium";
  return "low";
}

function scoreFundingReadiness(profile: GoClearTestProfile): "low" | "medium" | "high" {
  let score = 0;
  if (profile.credit_utilization_pct <= 30) score += 2;
  else if (profile.credit_utilization_pct <= 55) score++;
  if (profile.has_business_entity) score++;
  if (profile.has_business_bank_account) score++;
  if (profile.time_in_business_months >= 12) score++;
  if (profile.annual_revenue >= 50000) score++;
  if (score >= 5) return "high";
  if (score >= 3) return "medium";
  return "low";
}

function scoreDocumentationReadiness(profile: GoClearTestProfile): "low" | "medium" | "high" {
  let score = 0;
  if (profile.has_business_entity) score++;
  if (profile.has_business_bank_account) score++;
  if (profile.has_business_website) score++;
  if (profile.has_business_email) score++;
  if (profile.has_business_phone) score++;
  if (score >= 4) return "high";
  if (score >= 2) return "medium";
  return "low";
}

function scoreClientEducationNeed(profile: GoClearTestProfile): "low" | "medium" | "high" {
  const utilization = profile.credit_utilization_pct;
  const hasEntity = profile.has_business_entity;
  if (utilization > 55 && !hasEntity) return "high";
  if (utilization > 30 || !hasEntity) return "medium";
  return "low";
}

function determineRayReviewPriority(profile: GoClearTestProfile): "low" | "medium" | "high" {
  if (profile.credit_utilization_pct > 55 || !profile.has_business_entity) return "high";
  if (profile.credit_utilization_pct > 30 || !profile.has_business_bank_account) return "medium";
  return "low";
}

function buildMissingInformation(profile: GoClearTestProfile): string[] {
  const missing: string[] = [];
  if (!profile.has_business_entity) missing.push("Business entity formation (LLC/Corp)");
  if (!profile.has_business_bank_account) missing.push("Business bank account");
  if (!profile.has_business_website) missing.push("Business website/domain");
  if (!profile.has_business_email) missing.push("Professional business email");
  if (!profile.has_business_phone) missing.push("Dedicated business phone line");
  if (profile.time_in_business_months < 6) missing.push("Additional time in business");
  if (profile.annual_revenue < 25000) missing.push("Revenue documentation");
  return missing;
}

function buildRiskCautions(profile: GoClearTestProfile): string[] {
  const cautions: string[] = [];
  cautions.push("All outputs are draft-only and unverified");
  cautions.push("No funding guarantees — internal readiness assessment only");
  cautions.push("No score-increase guarantees");
  cautions.push("No automated lender applications");
  if (profile.credit_utilization_pct > 55) {
    cautions.push("High utilization — do not recommend specific payoff strategies");
  }
  if (!profile.has_business_entity) {
    cautions.push("No business entity — do not provide legal advice about formation");
  }
  return cautions;
}

function buildBlockedActions(_profile: GoClearTestProfile): string[] {
  return [
    "no_send",
    "no_publish",
    "no_charge",
    "no_trade",
    "no_automated_disputes",
    "no_direct_lender_applications",
    "no_guaranteed_approvals",
    "no_score_increase_guarantees",
    "no_funding_guarantees",
    "no_deletion_guarantees",
  ];
}

function buildCreditUtilizationNotes(profile: GoClearTestProfile): string {
  const pct = profile.credit_utilization_pct;
  if (pct <= 30) {
    return `Utilization at ${pct}% — within general recommended range. Readiness level: high. No urgent action needed for utilization. Admin should verify actual credit report details before any client-facing guidance.`;
  }
  if (pct <= 55) {
    return `Utilization at ${pct}% — above general recommended range. Readiness level: medium. Reducing utilization may improve funding readiness. Admin should note this as an area for client education. No specific payoff advice without Ray Review.`;
  }
  return `Utilization at ${pct}% — significantly above recommended range. Readiness level: low. High utilization may impact funding readiness. Admin should flag for readiness education. No score-increase guarantees. No specific payoff advice.`;
}

function buildBusinessSetupNotes(profile: GoClearTestProfile): string {
  const parts: string[] = [];
  if (!profile.has_business_entity) {
    parts.push(`No business entity (${profile.entity_type}). Entity formation is a foundational step for bankability.`);
  } else {
    parts.push(`Business entity: ${profile.entity_type}. Entity formation complete.`);
  }
  if (!profile.has_business_bank_account) {
    parts.push("No business bank account yet. Business banking is required for funding readiness.");
  }
  if (!profile.has_business_website || !profile.has_business_email || !profile.has_business_phone) {
    const missing: string[] = [];
    if (!profile.has_business_website) missing.push("website");
    if (!profile.has_business_email) missing.push("email");
    if (!profile.has_business_phone) missing.push("phone");
    parts.push(`Missing business infrastructure: ${missing.join(", ")}.`);
  }
  if (profile.time_in_business_months < 6) {
    parts.push(`Time in business: ${profile.time_in_business_months} months. Newer entities have fewer funding options.`);
  } else {
    parts.push(`Time in business: ${profile.time_in_business_months} months.`);
  }
  return parts.join(" ");
}

function generateAdminReadinessNote(
  profile: GoClearTestProfile,
  scorecard: ReadinessScorecardDraft,
): AdminReadinessNote {
  return {
    profile_id: profile.profile_id,
    profile_label: profile.profile_label,
    credit_utilization_notes: buildCreditUtilizationNotes(profile),
    business_setup_notes: buildBusinessSetupNotes(profile),
    missing_information: buildMissingInformation(profile),
    internal_recommendation: `Process through GoClear readiness review workflow. Ray Review priority: ${scorecard.ray_review_priority}. Categories used: credit_utilization, business_setup, manual_notes.`,
    risk_compliance_cautions: buildRiskCautions(profile),
    blocked_actions: buildBlockedActions(profile),
    ray_review_required: true,
    generated_at: new Date().toISOString(),
    output_label: "INTERNAL TEST ONLY — DRAFT — NOT CLIENT-FACING — RAY REVIEW REQUIRED",
  };
}

function generateRayReviewDraft(
  profile: GoClearTestProfile,
  scorecard: ReadinessScorecardDraft,
): RayReviewDraftForProfile {
  return {
    title: `GoClear Readiness Review — ${profile.profile_label} Profile (${profile.profile_id})`,
    profile_summary: `${profile.profile_label} hypothetical profile. Utilization: ${profile.credit_utilization_pct}%. Entity: ${profile.entity_type}. Revenue: $${profile.annual_revenue}. Score range: ${profile.credit_score_range}. Funding goal: $${profile.funding_goal}.`,
    recommended_next_step: `Ray should review this profile for internal readiness assessment. Priority: ${scorecard.ray_review_priority}. Readiness notes generated. No client-facing output approved.`,
    why_it_matters: `This tests the GoClear $97 Credit & Funding Readiness Review workflow using a hypothetical profile. Validates that the internal test runner produces safe, admin-only, draft-only outputs.`,
    what_ray_should_approve_reject: `Approve: internal admin notes for readiness assessment. Reject: any client-facing output, any funding guarantees, any score-increase promises.`,
    what_must_not_be_client_facing_yet: [
      "All readiness notes are admin-only",
      "No funding recommendations approved",
      "No score-increase promises",
      "No automated lender applications",
      "No specific payoff advice",
      "No legal/tax advice",
    ],
    blocked_guarantees: [
      "No funding approval guarantees",
      "No score-increase guarantees",
      "No deletion guarantees",
      "No approval guarantees",
    ],
    client_facing_allowed: "no",
    approval_required: true,
    generated_at: new Date().toISOString(),
    output_label: "INTERNAL TEST ONLY — DRAFT — NOT CLIENT-FACING — RAY REVIEW REQUIRED",
  };
}

function buildScorecard(profile: GoClearTestProfile): ReadinessScorecardDraft {
  return {
    credit_utilization_readiness: scoreUtilization(profile.credit_utilization_pct),
    business_setup_readiness: scoreBusinessSetup(profile),
    funding_readiness_preparation: scoreFundingReadiness(profile),
    documentation_readiness: scoreDocumentationReadiness(profile),
    client_education_need: scoreClientEducationNeed(profile),
    ray_review_priority: determineRayReviewPriority(profile),
  };
}

export function runInternalTestProfile(profile: GoClearTestProfile): InternalTestResult {
  const scorecard = buildScorecard(profile);
  const adminNote = generateAdminReadinessNote(profile, scorecard);
  const rayReviewDraft = generateRayReviewDraft(profile, scorecard);

  return {
    profile_id: profile.profile_id,
    profile_label: profile.profile_label,
    admin_readiness_note: adminNote,
    ray_review_draft: rayReviewDraft,
    readiness_scorecard: scorecard,
  };
}

export function loadAllProfiles(): GoClearTestProfile[] {
  const files = readdirSync(FIXTURES_DIR).filter((f: string) => f.endsWith(".json"));
  return files.map((f: string) => loadProfile(f));
}

export function runAllProfiles(): InternalTestResult[] {
  const profiles = loadAllProfiles();
  return profiles.map((p: GoClearTestProfile) => runInternalTestProfile(p));
}

export function generateManifest(results: InternalTestResult[]): InternalTestManifest {
  return {
    generated_at: new Date().toISOString(),
    total_profiles: results.length,
    categories_used: [...APPROVED_CATEGORIES],
    profiles: results.map(r => ({
      profile_id: r.profile_id,
      profile_label: r.profile_label,
      ray_review_priority: r.readiness_scorecard.ray_review_priority,
    })),
    output_label: "INTERNAL TEST ONLY — DRAFT — NOT CLIENT-FACING — RAY REVIEW REQUIRED",
  };
}

export function writeTestResults(results: InternalTestResult[]): void {
  mkdirSync(RESULTS_DIR, { recursive: true });
  mkdirSync(REPORTS_DIR, { recursive: true });

  const manifest = generateManifest(results);

  writeFileSync(
    join(RESULTS_DIR, "latest_internal_test_manifest.json"),
    JSON.stringify(manifest, null, 2),
  );

  const summaryLines: string[] = [
    "# GoClear Readiness Internal Test Runner — Summary",
    "",
    `**Generated**: ${new Date().toISOString()}`,
    "",
    "---",
    "",
    "## Profile Results",
    "",
  ];

  for (const r of results) {
    summaryLines.push(`### ${r.profile_label} (${r.profile_id})`);
    summaryLines.push("");
    summaryLines.push("| Metric | Value |");
    summaryLines.push("|--------|-------|");
    summaryLines.push(`| Credit Utilization | ${r.readiness_scorecard.credit_utilization_readiness} |`);
    summaryLines.push(`| Business Setup | ${r.readiness_scorecard.business_setup_readiness} |`);
    summaryLines.push(`| Funding Readiness | ${r.readiness_scorecard.funding_readiness_preparation} |`);
    summaryLines.push(`| Documentation | ${r.readiness_scorecard.documentation_readiness} |`);
    summaryLines.push(`| Client Education Need | ${r.readiness_scorecard.client_education_need} |`);
    summaryLines.push(`| Ray Review Priority | ${r.readiness_scorecard.ray_review_priority} |`);
    summaryLines.push("");
  }

  summaryLines.push("---");
  summaryLines.push("");
  summaryLines.push("## Blocked Actions");
  summaryLines.push("");
  summaryLines.push("- No client-facing output");
  summaryLines.push("- No funding guarantees");
  summaryLines.push("- No score-increase guarantees");
  summaryLines.push("- No automated disputes");
  summaryLines.push("- No automated lender applications");
  summaryLines.push("- No send/publish/charge/trade");
  summaryLines.push("");
  summaryLines.push("---");
  summaryLines.push("");
  summaryLines.push(`Output label: ${manifest.output_label}`);

  writeFileSync(join(RESULTS_DIR, "latest_internal_test_summary.md"), summaryLines.join("\n"));

  const outputsLines: string[] = [
    "# GoClear Internal Test Runner — Outputs",
    "",
    `**Generated**: ${new Date().toISOString()}`,
    "",
    "---",
    "",
  ];

  for (const r of results) {
    outputsLines.push(`## ${r.admin_readiness_note.profile_label} — Admin Readiness Note`);
    outputsLines.push("");
    outputsLines.push(`**Output label**: ${r.admin_readiness_note.output_label}`);
    outputsLines.push("");
    outputsLines.push("### Credit Utilization Notes");
    outputsLines.push(r.admin_readiness_note.credit_utilization_notes);
    outputsLines.push("");
    outputsLines.push("### Business Setup Notes");
    outputsLines.push(r.admin_readiness_note.business_setup_notes);
    outputsLines.push("");
    outputsLines.push("### Missing Information");
    for (const m of r.admin_readiness_note.missing_information) {
      outputsLines.push(`- ${m}`);
    }
    outputsLines.push("");
    outputsLines.push("### Internal Recommendation");
    outputsLines.push(r.admin_readiness_note.internal_recommendation);
    outputsLines.push("");
    outputsLines.push("### Risk/Compliance Cautions");
    for (const c of r.admin_readiness_note.risk_compliance_cautions) {
      outputsLines.push(`- ${c}`);
    }
    outputsLines.push("");
    outputsLines.push("### Blocked Actions");
    for (const b of r.admin_readiness_note.blocked_actions) {
      outputsLines.push(`- ${b}`);
    }
    outputsLines.push("");
    outputsLines.push("---");
    outputsLines.push("");
  }

  writeFileSync(join(REPORTS_DIR, "goclear_internal_test_outputs.md"), outputsLines.join("\n"));

  const rayReviewLines: string[] = [
    "# GoClear Internal Test Runner — Ray Review Drafts",
    "",
    `**Generated**: ${new Date().toISOString()}`,
    "",
    "---",
    "",
  ];

  for (const r of results) {
    rayReviewLines.push(`## ${r.ray_review_draft.title}`);
    rayReviewLines.push("");
    rayReviewLines.push(`**Output label**: ${r.ray_review_draft.output_label}`);
    rayReviewLines.push("");
    rayReviewLines.push("### Profile Summary");
    rayReviewLines.push(r.ray_review_draft.profile_summary);
    rayReviewLines.push("");
    rayReviewLines.push("### Recommended Next Step");
    rayReviewLines.push(r.ray_review_draft.recommended_next_step);
    rayReviewLines.push("");
    rayReviewLines.push("### Why It Matters");
    rayReviewLines.push(r.ray_review_draft.why_it_matters);
    rayReviewLines.push("");
    rayReviewLines.push("### What Ray Should Approve/Reject");
    rayReviewLines.push(r.ray_review_draft.what_ray_should_approve_reject);
    rayReviewLines.push("");
    rayReviewLines.push("### What Must Not Be Client-Facing Yet");
    for (const item of r.ray_review_draft.what_must_not_be_client_facing_yet) {
      rayReviewLines.push(`- ${item}`);
    }
    rayReviewLines.push("");
    rayReviewLines.push("### Blocked Guarantees");
    for (const g of r.ray_review_draft.blocked_guarantees) {
      rayReviewLines.push(`- ${g}`);
    }
    rayReviewLines.push("");
    rayReviewLines.push(`- Client-facing allowed: ${r.ray_review_draft.client_facing_allowed}`);
    rayReviewLines.push(`- Approval required: ${r.ray_review_draft.approval_required}`);
    rayReviewLines.push("");
    rayReviewLines.push("---");
    rayReviewLines.push("");
  }

  writeFileSync(join(REPORTS_DIR, "goclear_internal_ray_review_drafts.md"), rayReviewLines.join("\n"));
}
