import { readFileSync, writeFileSync, readdirSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const ROOT = dirname(dirname(dirname(__filename)));
const FIXTURES_DIR = join(ROOT, "nexus_research", "internal_test_runner", "fixtures");

const REPORT_LABEL = "INTERNAL DRAFT — NOT CLIENT-FACING — RAY REVIEW REQUIRED";

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

export interface InternalReadinessReport {
  profile_id: string;
  profile_label: string;
  report_label: string;
  cover_summary: string;
  profile_type: string;
  credit_utilization_readiness: string;
  business_setup_readiness: string;
  fundability_preparation: string;
  missing_information: string[];
  internal_admin_notes: string[];
  ray_review_required_items: string[];
  blocked_actions: string[];
  draft_client_education_concepts: string[];
  compliance_cautions: string[];
  next_internal_step: string;
  generated_at: string;
}

function loadProfile(filename: string): GoClearTestProfile {
  const raw = readFileSync(join(FIXTURES_DIR, filename), "utf-8");
  const jsonStr = raw.replace(/^HYPOTHETICAL INTERNAL TEST PROFILE.*\n\n/, "");
  return JSON.parse(jsonStr);
}

function loadAllProfiles(): GoClearTestProfile[] {
  const files = readdirSync(FIXTURES_DIR).filter((f: string) => f.endsWith(".json"));
  return files.map(f => loadProfile(f));
}

function scoreUtilization(pct: number): "low" | "medium" | "high" {
  if (pct <= 30) return "high";
  if (pct <= 55) return "medium";
  return "low";
}

function scoreBusinessSetup(p: GoClearTestProfile): "low" | "medium" | "high" {
  let s = 0;
  if (p.has_business_entity) s++;
  if (p.has_business_bank_account) s++;
  if (p.has_business_website) s++;
  if (p.has_business_email) s++;
  if (p.has_business_phone) s++;
  if (p.time_in_business_months >= 6) s++;
  return s >= 5 ? "high" : s >= 3 ? "medium" : "low";
}

function scoreFunding(p: GoClearTestProfile): "low" | "medium" | "high" {
  let s = 0;
  if (p.credit_utilization_pct <= 30) s += 2;
  else if (p.credit_utilization_pct <= 55) s++;
  if (p.has_business_entity) s++;
  if (p.has_business_bank_account) s++;
  if (p.time_in_business_months >= 12) s++;
  if (p.annual_revenue >= 50000) s++;
  return s >= 5 ? "high" : s >= 3 ? "medium" : "low";
}

function scoreDocumentation(p: GoClearTestProfile): "low" | "medium" | "high" {
  let s = 0;
  if (p.has_business_entity) s++;
  if (p.has_business_bank_account) s++;
  if (p.has_business_website) s++;
  if (p.has_business_email) s++;
  if (p.has_business_phone) s++;
  return s >= 4 ? "high" : s >= 2 ? "medium" : "low";
}

function scoreClientEdNeed(p: GoClearTestProfile): "low" | "medium" | "high" {
  if (p.credit_utilization_pct > 55 && !p.has_business_entity) return "high";
  if (p.credit_utilization_pct > 30 || !p.has_business_entity) return "medium";
  return "low";
}

function scoreRayPriority(p: GoClearTestProfile): "low" | "medium" | "high" {
  if (p.credit_utilization_pct > 55 || !p.has_business_entity) return "high";
  if (p.credit_utilization_pct > 30 || !p.has_business_bank_account) return "medium";
  return "low";
}

function buildScorecard(p: GoClearTestProfile): ReadinessScorecardDraft {
  return {
    credit_utilization_readiness: scoreUtilization(p.credit_utilization_pct),
    business_setup_readiness: scoreBusinessSetup(p),
    funding_readiness_preparation: scoreFunding(p),
    documentation_readiness: scoreDocumentation(p),
    client_education_need: scoreClientEdNeed(p),
    ray_review_priority: scoreRayPriority(p),
  };
}

function buildMissingInfo(p: GoClearTestProfile): string[] {
  const m: string[] = [];
  if (!p.has_business_entity) m.push("Business entity formation (LLC/Corp)");
  if (!p.has_business_bank_account) m.push("Business bank account");
  if (!p.has_business_website) m.push("Business website/domain");
  if (!p.has_business_email) m.push("Professional business email");
  if (!p.has_business_phone) m.push("Dedicated business phone line");
  if (p.time_in_business_months < 6) m.push("Additional time in business");
  if (p.annual_revenue < 25000) m.push("Revenue documentation");
  return m;
}

function buildCreditNotes(p: GoClearTestProfile): string {
  const pct = p.credit_utilization_pct;
  if (pct <= 30) return `Utilization at ${pct}% — within general recommended range. Readiness level: high. No urgent action needed. Admin should verify actual credit report details before any client-facing guidance.`;
  if (pct <= 55) return `Utilization at ${pct}% — above general recommended range. Readiness level: medium. Reducing utilization may improve funding readiness. No specific payoff advice without Ray Review.`;
  return `Utilization at ${pct}% — significantly above recommended range. Readiness level: low. High utilization impacts funding readiness. No score-increase guarantees. No specific payoff advice.`;
}

function buildBusinessNotes(p: GoClearTestProfile): string {
  const parts: string[] = [];
  if (!p.has_business_entity) parts.push(`No business entity (${p.entity_type}). Entity formation is foundational for bankability.`);
  else parts.push(`Business entity: ${p.entity_type}. Formation complete.`);
  if (!p.has_business_bank_account) parts.push("No business bank account. Required for funding readiness.");
  const infra: string[] = [];
  if (!p.has_business_website) infra.push("website");
  if (!p.has_business_email) infra.push("email");
  if (!p.has_business_phone) infra.push("phone");
  if (infra.length) parts.push(`Missing infrastructure: ${infra.join(", ")}.`);
  parts.push(`Time in business: ${p.time_in_business_months} months.`);
  return parts.join(" ");
}

function buildComplianceCautions(p: GoClearTestProfile): string[] {
  const c: string[] = [];
  c.push("All outputs are draft-only and unverified");
  c.push("No funding guarantees — internal readiness assessment only");
  c.push("No score-increase guarantees");
  c.push("No automated lender applications");
  if (p.credit_utilization_pct > 55) c.push("High utilization — do not recommend specific payoff strategies");
  if (!p.has_business_entity) c.push("No entity — do not provide legal advice about formation");
  return c;
}

function buildBlockedActions(): string[] {
  return [
    "no_send", "no_publish", "no_charge", "no_trade",
    "no_automated_disputes", "no_direct_lender_applications",
    "no_guaranteed_approvals", "no_score_increase_guarantees",
    "no_funding_guarantees", "no_deletion_guarantees",
  ];
}

export function generateReadinessReport(profile: GoClearTestProfile): InternalReadinessReport {
  const sc = buildScorecard(profile);
  return {
    profile_id: profile.profile_id,
    profile_label: profile.profile_label,
    report_label: REPORT_LABEL,
    cover_summary: `GoClear $97 Credit & Funding Readiness Review — Internal Draft for ${profile.profile_label} profile (${profile.profile_id}). Hypothetical profile. All outputs draft-only. Ray Review required before any client-facing use.`,
    profile_type: `Hypothetical ${profile.profile_label} — utilization ${profile.credit_utilization_pct}%, entity ${profile.entity_type}, revenue $${profile.annual_revenue}, score range ${profile.credit_score_range}`,
    credit_utilization_readiness: buildCreditNotes(profile),
    business_setup_readiness: buildBusinessNotes(profile),
    fundability_preparation: `Fundability readiness: ${sc.funding_readiness_preparation}. Documentation readiness: ${sc.documentation_readiness}. Business setup readiness: ${sc.business_setup_readiness}.`,
    missing_information: buildMissingInfo(profile),
    internal_admin_notes: [
      `Ray Review priority: ${sc.ray_review_priority}`,
      `Categories used: credit_utilization, business_setup, manual_notes`,
      `Scorecard generated — draft only, not approved`,
      `No client-facing output approved`,
    ],
    ray_review_required_items: [
      "All readiness notes require Ray Review",
      "No funding recommendations approved",
      "No score-increase promises approved",
      "No automated lender applications",
      "No specific payoff advice approved",
    ],
    blocked_actions: buildBlockedActions(),
    draft_client_education_concepts: [
      "General credit utilization education (draft)",
      "Business setup readiness education (draft)",
      "Funding readiness preparation education (draft)",
    ],
    compliance_cautions: buildComplianceCautions(profile),
    next_internal_step: `Ray should review this ${profile.profile_label} profile readiness assessment. Priority: ${sc.ray_review_priority}. All outputs are internal draft-only.`,
    generated_at: new Date().toISOString(),
  };
}

export function generateAllReports(): InternalReadinessReport[] {
  return loadAllProfiles().map(p => generateReadinessReport(p));
}

export function writeAllReports(reports: InternalReadinessReport[]): void {
  const outDir = join(ROOT, "reports", "nexus_research", "internal_test_runner", "readiness_reports");
  mkdirSync(outDir, { recursive: true });

  const slugMap: Record<string, string> = {
    "TEST-001": "starter_profile",
    "TEST-002": "improving_profile",
    "TEST-003": "stronger_profile",
  };

  for (const r of reports) {
    const slug = slugMap[r.profile_id] || r.profile_id.toLowerCase();
    const lines: string[] = [
      `# GoClear Readiness Review — ${r.profile_label} Internal Readiness Report`,
      "",
      `**Generated**: ${r.generated_at}`,
      "",
      `**Report Label**: ${r.report_label}`,
      "",
      "---",
      "",
      "## 1. Internal Cover Summary",
      "",
      r.cover_summary,
      "",
      "---",
      "",
      "## 2. Profile Type",
      "",
      r.profile_type,
      "",
      "---",
      "",
      "## 3. Credit Utilization Readiness",
      "",
      r.credit_utilization_readiness,
      "",
      "---",
      "",
      "## 4. Business Setup Readiness",
      "",
      r.business_setup_readiness,
      "",
      "---",
      "",
      "## 5. Fundability Preparation",
      "",
      r.fundability_preparation,
      "",
      "---",
      "",
      "## 6. Missing Information",
      "",
      ...r.missing_information.map(m => `- ${m}`),
      "",
      "---",
      "",
      "## 7. Internal Admin Notes",
      "",
      ...r.internal_admin_notes.map(n => `- ${n}`),
      "",
      "---",
      "",
      "## 8. Ray Review Required Items",
      "",
      ...r.ray_review_required_items.map(i => `- ${i}`),
      "",
      "---",
      "",
      "## 9. Blocked Actions",
      "",
      ...r.blocked_actions.map(b => `- ${b}`),
      "",
      "---",
      "",
      "## 10. Draft Client Education Concepts",
      "",
      ...r.draft_client_education_concepts.map(d => `- ${d}`),
      "",
      "---",
      "",
      "## 11. Compliance Cautions",
      "",
      ...r.compliance_cautions.map(c => `- ${c}`),
      "",
      "---",
      "",
      "## 12. Next Internal Step",
      "",
      r.next_internal_step,
      "",
      "---",
      "",
      `Report label: ${r.report_label}`,
    ];
    writeFileSync(join(outDir, `${slug}_internal_readiness_report.md`), lines.join("\n"));
  }

  const summaryLines: string[] = [
    "# GoClear Readiness Report Builder — Summary",
    "",
    `**Generated**: ${new Date().toISOString()}`,
    "",
    `**Report Label**: ${REPORT_LABEL}`,
    "",
    "---",
    "",
    "## Reports Generated",
    "",
    "| Profile | Report |",
    "|---------|--------|",
    ...reports.map(r => `| ${r.profile_label} | ${slugMap[r.profile_id]}_internal_readiness_report.md |`),
    "",
    "---",
    "",
    "## Categories Used",
    "",
    "- manual_notes",
    "- credit_utilization",
    "- business_setup",
    "",
    "---",
    "",
    "## Blocked Actions",
    "",
    ...buildBlockedActions().map(b => `- ${b}`),
    "",
    "---",
    "",
    `Report label: ${REPORT_LABEL}`,
  ];
  writeFileSync(join(outDir, "readiness_report_builder_summary.md"), summaryLines.join("\n"));
}
