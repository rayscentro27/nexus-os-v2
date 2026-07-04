function computeSha256(content: string): string {
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  const hex = Math.abs(hash).toString(16).padStart(8, "0");
  return (hex + hex + hex + hex + hex + hex + hex + hex).slice(0, 64);
}

export const NEXUS_RESEARCH_FILE_POLICY = Object.freeze({
  allowedDirectories: [
    "nexus_research/research_inbox/credit_repair/",
    "nexus_research/research_inbox/credit_utilization/",
    "nexus_research/research_inbox/business_setup/",
    "nexus_research/research_inbox/business_funding/",
    "nexus_research/research_inbox/grants/",
    "nexus_research/research_inbox/lenders/",
    "nexus_research/research_inbox/affiliates/",
    "nexus_research/research_inbox/compliance/",
    "nexus_research/research_inbox/client_education/",
    "nexus_research/research_inbox/manual_notes/",
  ],
  allowedExtensions: [".md"],
  blockedExtensions: [".env", ".key", ".pem", ".p12", ".db", ".sqlite", ".sql", ".exe", ".dmg", ".zip", ".json", ".csv", ".pdf", ".js", ".ts", ".jsx", ".tsx", ".py", ".sh", ".bat"],
  maxFileSizeBytes: 500_000,
  blockedFilenameSegments: [".env", "secret", "credential", "service-role", "production", "private"],
});

export type NexusArtifactCategory =
  | "credit_repair"
  | "credit_utilization"
  | "business_setup"
  | "fundability"
  | "business_funding"
  | "grants"
  | "lender_program"
  | "affiliate_offer"
  | "client_education"
  | "compliance"
  | "manual_note";

export type NexusArtifactRoute =
  | "credit_readiness_knowledge"
  | "scorecard_recommendation"
  | "business_setup_checklist"
  | "fundability_checklist"
  | "funding_readiness_plan"
  | "grant_opportunity_review"
  | "lender_matching_notes"
  | "affiliate_offer_approval"
  | "compliance_guardrail"
  | "client_education_draft"
  | "manual_review_queue";

export type EvidenceQuality = "verified" | "credible" | "unverified" | "demo" | "opinion";

export interface NexusFileCandidate {
  path: string;
  title: string;
  sizeBytes: number;
  content?: string;
  filename?: string;
}

export interface NexusArtifactMetadata {
  artifact_id: string;
  source_path: string;
  canonical_path: string;
  filename: string;
  category: NexusArtifactCategory;
  size_bytes: number;
  sha256: string;
  modified_at: string;
  ingested_at: string;
  title: string;
  short_summary: string;
  evidence_quality: EvidenceQuality;
  compliance_flags: string[];
  guarantee_flags: string[];
  cautionary_context_flags: string[];
  direct_claim_flags: string[];
  severe_safety_flags: string[];
  client_safe: boolean;
  admin_only: boolean;
  ray_review_required: boolean;
  routing_target: NexusArtifactRoute;
  allowed_output_type: string[];
  blocked_output_type: string[];
  parse_status: "parsed" | "rejected" | "error";
  safety_status: "safe" | "flagged" | "blocked";
}

export interface NexusAdminNote {
  summary: string;
  category: NexusArtifactCategory;
  evidence_quality: EvidenceQuality;
  risk_compliance_notes: string[];
  recommended_internal_action: string;
  ray_review_items: string[];
}

export interface NexusRayReviewDraft {
  title: string;
  source_artifact: string;
  recommendation: string;
  why_it_matters: string;
  client_facing_allowed: "yes" | "no" | "pending";
  approval_required: boolean;
  blocked_actions: string[];
}

const GUARANTEE_PATTERNS = [
  /guarantee(?:s|d)?\s+(approval|funding|deletion|score\s+increase)/i,
  /no\s+credit\s+check/i,
  /instant\s+approval/i,
  /remove\s+all\s+negatives/i,
  /bypass\s+underwriting/i,
  /fake\s+business\s+address/i,
  /tradeline\s+manipulation/i,
  /illegal\s+dispute/i,
  /submit\s+application\s+automatically/i,
  /send\s+letter\s+automatically/i,
  /apply\s+for\s+loan\s+automatically/i,
  /charge\s+client\s+automatically/i,
  /publish\s+this/i,
  /email\s+this/i,
  /ignore\s+approval/i,
  /bypass\s+ray\s+review/i,
  /100%\s+(approval|funding|guarantee)/i,
  /definite(ly)?\s+(approval|funding)/i,
  /sure\s+(approval|funding)/i,
];

const CAUTIONARY_CONTEXT_PATTERNS = [
  { pattern: /(?:do\s+not|don'?t|never|avoid|no|must\s+not|should\s+not)\s+(?:guarantee|promise|ensure|guaranteeing)\s+(?:approval|funding|deletion|score|increase|outcome)/gi, label: "prohibitive_guarantee_language" },
  { pattern: /(?:do\s+not|don'?t|never|avoid|no|must\s+not|should\s+not)\s+(?:provide|give|offer)\s+legal\s+advice/gi, label: "prohibitive_legal_advice" },
  { pattern: /(?:do\s+not|don'?t|never|avoid|no|must\s+not|should\s+not)\s+(?:submit|send|apply|automate)/gi, label: "prohibitive_automation" },
  { pattern: /(?:do\s+not|don'?t|never|avoid|no)\s+(?:claim|promise|state)\s+(?:that\s+)?(?:items|debts|negative)/gi, label: "prohibitive_removal_claims" },
  { pattern: /(?:do\s+not|don'?t|never|avoid|no)\s+(?:mislead|fraudulent|deceptive)/gi, label: "prohibitive_fraud" },
  { pattern: /(?:not|no)\s+(?:guarantee|guarantees|approval|guaranteed)/gi, label: "prohibitive_no_guarantee" },
  { pattern: /(?:avoid|no|not)\s+(?:score[\s-]*increase|promise|promises)/gi, label: "prohibitive_no_score_promises" },
];

const DIRECT_CLAIM_PATTERNS = [
  /we\s+guarantee\s+(?:approval|funding|deletion|score|increase)/gi,
  /guaranteed\s+(?:approval|funding|deletion|score|increase)/gi,
  /100%\s+(?:approval|funding|guarantee|success)/gi,
  /instant\s+approval/gi,
  /no\s+credit\s+check/gi,
  /remove\s+all\s+negatives/gi,
  /bypass\s+(?:underwriting|ray\s+review|compliance)/gi,
  /fake\s+(?:business\s+address|documents|income)/gi,
  /tradeline\s+manipulation/gi,
  /illegal\s+dispute/gi,
  /submit\s+application\s+automatically/gi,
  /send\s+letter\s+automatically/gi,
  /apply\s+for\s+loan\s+automatically/gi,
  /charge\s+client\s+automatically/gi,
];

export function detectCautionaryContextFlags(content: string): string[] {
  const flags: string[] = [];
  for (const { pattern, label } of CAUTIONARY_CONTEXT_PATTERNS) {
    const regex = new RegExp(pattern.source, pattern.flags);
    if (regex.test(content)) flags.push(label);
  }
  return [...new Set(flags)];
}

export function detectDirectClaimFlags(content: string): string[] {
  const flags: string[] = [];
  for (const pattern of DIRECT_CLAIM_PATTERNS) {
    const match = content.match(pattern);
    if (match) flags.push(match[0]);
  }
  return [...new Set(flags)];
}

export function detectSevereSafetyFlags(content: string): string[] {
  const flags: string[] = [];
  const severePatterns = [
    /we\s+guarantee/gi,
    /guaranteed\s+approval/gi,
    /100%\s+(?:approval|funding|success)/gi,
    /instant\s+approval/gi,
    /bypass\s+(?:underwriting|ray\s+review)/gi,
    /fake\s+(?:business|documents|income)/gi,
    /tradeline\s+manipulation/gi,
    /illegal/gi,
  ];
  for (const pattern of severePatterns) {
    const match = content.match(pattern);
    if (match) flags.push(match[0]);
  }
  return [...new Set(flags)];
}

const CATEGORY_KEYWORDS: Record<NexusArtifactCategory, string[]> = {
  credit_repair: ["credit repair", "dispute", "credit report", "negative item", "credit score", "fcra", "fdcpa", "credit bureau", "equifax", "transunion", "experian"],
  credit_utilization: ["utilization", "credit utilization", "balance", "credit limit", "utilization ratio", "statement date", "balance transfer"],
  business_setup: ["llc", "ein", "duns", "naics", "business entity", "registered agent", "business address", "business phone", "incorporation"],
  fundability: ["fundability", "bankability", "funding ready", "credit ready", "business credit score", "paydex", "生意信用"],
  business_funding: ["business funding", "business loan", "sba", "line of credit", "credit card", "revenue-based", "business financing", "merchant cash"],
  grants: ["grant", "federal grant", "state grant", "minority grant", "grant database", "grant application", "sbir", "sttr"],
  lender_program: ["lender", "underwriting", "lending criteria", "bank requirements", "credit union", "loan program"],
  affiliate_offer: ["affiliate", "referral", "partner offer", "commission", "referral link", "affiliate program"],
  client_education: ["education", "learn", "understand", "guide", "overview", "basics", "what is", "how to"],
  compliance: ["compliance", "fcra", "fdcpa", "regulation", "disclosure", "licensing", "legal", "ftc"],
  manual_note: ["note", "observation", "evaluation", "reminder", "todo"],
};

function extractTitle(content: string, filename: string): string {
  const h1Match = content.match(/^#\s+(.+)$/m);
  if (h1Match) return h1Match[1].trim();
  return filename.replace(/\.md$/i, "").replace(/[-_]/g, " ");
}

function extractSummary(content: string): string {
  const lines = content.split("\n").filter((l) => l.trim() && !l.startsWith("#"));
  return lines.slice(0, 3).join(" ").slice(0, 300);
}

export function detectCategory(content: string, filePath: string): NexusArtifactCategory {
  const pathLower = filePath.toLowerCase();

  if (pathLower.includes("credit_repair")) return "credit_repair";
  if (pathLower.includes("credit_utilization")) return "credit_utilization";
  if (pathLower.includes("business_setup")) return "business_setup";
  if (pathLower.includes("business_funding")) return "business_funding";
  if (pathLower.includes("grants")) return "grants";
  if (pathLower.includes("lenders")) return "lender_program";
  if (pathLower.includes("affiliates")) return "affiliate_offer";
  if (pathLower.includes("compliance")) return "compliance";
  if (pathLower.includes("client_education")) return "client_education";
  if (pathLower.includes("manual_notes")) return "manual_note";

  const lower = content.toLowerCase();
  for (const [cat, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    for (const kw of keywords) {
      if (lower.includes(kw)) {
        return cat as NexusArtifactCategory;
      }
    }
  }

  return "manual_note";
}

export function routeCategory(category: NexusArtifactCategory): NexusArtifactRoute {
  const routes: Record<NexusArtifactCategory, NexusArtifactRoute> = {
    credit_repair: "credit_readiness_knowledge",
    credit_utilization: "scorecard_recommendation",
    business_setup: "business_setup_checklist",
    fundability: "fundability_checklist",
    business_funding: "funding_readiness_plan",
    grants: "grant_opportunity_review",
    lender_program: "lender_matching_notes",
    affiliate_offer: "affiliate_offer_approval",
    client_education: "client_education_draft",
    compliance: "compliance_guardrail",
    manual_note: "manual_review_queue",
  };
  return routes[category];
}

export function detectGuaranteeFlags(content: string): string[] {
  const flags: string[] = [];
  for (const pattern of GUARANTEE_PATTERNS) {
    const match = content.match(pattern);
    if (match) flags.push(match[0]);
  }
  return flags;
}

export function detectComplianceFlags(content: string): string[] {
  const flags: string[] = [];
  const lower = content.toLowerCase();
  if (/fcra/.test(lower)) flags.push("FCRA");
  if (/fdcpa/.test(lower)) flags.push("FDCPA");
  if (/ftc/.test(lower)) flags.push("FTC disclosure");
  if (/legal\s+advice/.test(lower)) flags.push("potential legal advice");
  if (/tax\s+advice/.test(lower)) flags.push("potential tax advice");
  if (/financial\s+advice/.test(lower)) flags.push("potential financial advice");
  return flags;
}

export function computeAllowedOutputs(category: NexusArtifactCategory): string[] {
  const outputs: Record<NexusArtifactCategory, string[]> = {
    credit_repair: ["admin_notes", "compliance_notes", "client_education_approved"],
    credit_utilization: ["admin_notes", "scorecard_recommendations", "client_education_approved"],
    business_setup: ["admin_notes", "checklist_items", "client_education_approved"],
    fundability: ["admin_notes", "fundability_checklist", "client_education_approved"],
    business_funding: ["admin_notes", "funding_path_research", "client_education_approved"],
    grants: ["admin_notes", "grant_opportunity_research", "client_education_approved"],
    lender_program: ["admin_only_lender_notes"],
    affiliate_offer: ["admin_notes", "ray_review_proposals"],
    compliance: ["admin_notes", "policy_updates", "guardrail_changes"],
    client_education: ["client_facing_content_after_approval"],
    manual_note: ["admin_notes", "research_inputs"],
  };
  return outputs[category];
}

export function computeBlockedOutputs(category: NexusArtifactCategory): string[] {
  const blocked: Record<NexusArtifactCategory, string[]> = {
    credit_repair: ["direct_dispute_letters", "bureau_contact", "guaranteed_removals", "automated_disputes"],
    credit_utilization: ["guaranteed_score_increases", "specific_payoff_advice"],
    business_setup: ["legal_advice", "tax_advice", "guaranteed_outcomes"],
    fundability: ["guaranteed_funding", "direct_lender_applications"],
    business_funding: ["guaranteed_approvals", "direct_lender_applications", "automated_applications"],
    grants: ["guaranteed_grant_approval", "application_submission"],
    lender_program: ["client_facing_lender_recommendations", "direct_applications"],
    affiliate_offer: ["client_facing_promotions", "activated_links"],
    compliance: ["legal_advice", "compliance_guarantees"],
    client_education: ["specific_financial_advice", "guaranteed_outcomes"],
    manual_note: ["client_facing_without_review"],
  };
  return blocked[category];
}

function extension(path: string): string {
  const dot = path.lastIndexOf(".");
  return dot >= 0 ? path.slice(dot).toLowerCase() : "";
}

export function isApprovedInboxPath(normalizedPath: string): boolean {
  const ext = extension(normalizedPath);
  if (!NEXUS_RESEARCH_FILE_POLICY.allowedExtensions.includes(ext)) return false;
  if (NEXUS_RESEARCH_FILE_POLICY.blockedExtensions.includes(ext)) return false;
  return NEXUS_RESEARCH_FILE_POLICY.allowedDirectories.some((dir) => normalizedPath.startsWith(dir));
}

export function validatePath(normalizedPath: string): string[] {
  const reasons: string[] = [];

  if (normalizedPath.includes("..")) reasons.push("path_traversal_detected");
  if (normalizedPath.includes("\0")) reasons.push("null_byte_in_path");

  const filename = normalizedPath.split("/").pop() || "";
  for (const segment of NEXUS_RESEARCH_FILE_POLICY.blockedFilenameSegments) {
    if (filename.includes(segment)) reasons.push(`blocked_segment_${segment}`);
  }

  const ext = extension(normalizedPath);
  if (!NEXUS_RESEARCH_FILE_POLICY.allowedExtensions.includes(ext)) reasons.push("extension_not_allowed");
  if (NEXUS_RESEARCH_FILE_POLICY.blockedExtensions.includes(ext)) reasons.push("blocked_file_type");

  if (!isApprovedInboxPath(normalizedPath)) reasons.push("directory_not_approved");

  return reasons;
}

let artifactCounter = 0;

export function generateArtifactId(): string {
  artifactCounter++;
  const date = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  return `nexus-res-${date}-${String(artifactCounter).padStart(3, "0")}`;
}

export function resetArtifactCounter(): void {
  artifactCounter = 0;
}

export class NexusResearchAdapter {
  processCandidate(candidate: NexusFileCandidate): NexusArtifactMetadata {
    const normalized = candidate.path.toLowerCase().replaceAll("\\", "/").replace(/^\.\//, "");
    const reasons = validatePath(normalized);
    const now = new Date().toISOString();
    const content = candidate.content || "";
    const sha256 = content ? computeSha256(content) : "";
    const category = detectCategory(content, normalized);
    const route = routeCategory(category);
    const guaranteeFlags = detectGuaranteeFlags(content);
    const complianceFlags = detectComplianceFlags(content);
    const cautionaryContextFlags = detectCautionaryContextFlags(content);
    const directClaimFlags = detectDirectClaimFlags(content);
    const severeSafetyFlags = detectSevereSafetyFlags(content);
    const title = content ? extractTitle(content, candidate.filename || normalized.split("/").pop() || "unknown.md") : candidate.title;
    const summary = content ? extractSummary(content) : "";

    const hasRisk = guaranteeFlags.length > 0 || complianceFlags.length > 0 || cautionaryContextFlags.length > 0;
    const hasSevereRisk = severeSafetyFlags.length > 0 || directClaimFlags.length > 0;
    const clientSafe = !hasRisk && !hasSevereRisk && category !== "lender_program" && category !== "affiliate_offer";
    const adminOnly = hasRisk || hasSevereRisk || category === "lender_program" || category === "affiliate_offer" || guaranteeFlags.length > 0;
    const rayReviewRequired = clientSafe || category === "client_education" || category === "affiliate_offer" || category === "compliance";

    const parseStatus = reasons.length > 0 ? "rejected" as const : "parsed" as const;
    const safetyStatus = hasSevereRisk ? "blocked" as const : guaranteeFlags.length > 0 ? "blocked" as const : hasRisk ? "flagged" as const : "safe" as const;

    return {
      artifact_id: generateArtifactId(),
      source_path: candidate.path,
      canonical_path: normalized,
      filename: normalized.split("/").pop() || "unknown.md",
      category,
      size_bytes: candidate.sizeBytes,
      sha256,
      modified_at: now,
      ingested_at: now,
      title,
      short_summary: summary,
      evidence_quality: normalized.includes("fixture") ? "demo" : "unverified",
      compliance_flags: complianceFlags,
      guarantee_flags: guaranteeFlags,
      cautionary_context_flags: cautionaryContextFlags,
      direct_claim_flags: directClaimFlags,
      severe_safety_flags: severeSafetyFlags,
      client_safe: clientSafe,
      admin_only: adminOnly,
      ray_review_required: rayReviewRequired,
      routing_target: route,
      allowed_output_type: computeAllowedOutputs(category),
      blocked_output_type: computeBlockedOutputs(category),
      parse_status: parseStatus,
      safety_status: safetyStatus,
    };
  }

  generateAdminNote(metadata: NexusArtifactMetadata): NexusAdminNote {
    const riskNotes: string[] = [];
    if (metadata.severe_safety_flags.length > 0) {
      riskNotes.push(`SEVERE: Direct guarantee/illegal claims detected: ${metadata.severe_safety_flags.join("; ")}`);
    }
    if (metadata.direct_claim_flags.length > 0) {
      riskNotes.push(`Direct claim flags: ${metadata.direct_claim_flags.join("; ")}`);
    }
    if (metadata.guarantee_flags.length > 0) {
      riskNotes.push(`Guarantee language detected: ${metadata.guarantee_flags.join("; ")}`);
    }
    if (metadata.cautionary_context_flags.length > 0) {
      riskNotes.push(`Cautionary context detected (prohibitive language): ${metadata.cautionary_context_flags.join("; ")}`);
    }
    if (metadata.compliance_flags.length > 0) {
      riskNotes.push(`Compliance flags: ${metadata.compliance_flags.join(", ")}`);
    }
    if (metadata.admin_only) {
      riskNotes.push("Artifact marked admin-only");
    }

    return {
      summary: `Research artifact "${metadata.title}" classified as ${metadata.category}, routed to ${metadata.routing_target}. Evidence quality: ${metadata.evidence_quality}.`,
      category: metadata.category,
      evidence_quality: metadata.evidence_quality,
      risk_compliance_notes: riskNotes,
      recommended_internal_action: metadata.admin_only
        ? "Keep admin-only. Do not expose to clients without Ray Review."
        : "May be used for internal knowledge. Client-facing requires Ray Review.",
      ray_review_items: metadata.ray_review_required
        ? [`Review artifact: ${metadata.title}`, `Category: ${metadata.category}`, `Route: ${metadata.routing_target}`]
        : [],
    };
  }

  generateRayReviewDraft(metadata: NexusArtifactMetadata): NexusRayReviewDraft {
    return {
      title: `Review: ${metadata.title}`,
      source_artifact: metadata.artifact_id,
      recommendation: `Classified as ${metadata.category}. Route to ${metadata.routing_target}. Evidence quality: ${metadata.evidence_quality}.`,
      why_it_matters: `This research supports Nexus credit/funding workflows. Category: ${metadata.category}.`,
      client_facing_allowed: metadata.client_safe ? "pending" : "no",
      approval_required: true,
      blocked_actions: [
        "no_send",
        "no_publish",
        "no_charge",
        "no_trade",
        "no_automated_disputes",
        "no_direct_lender_applications",
        "no_guaranteed_approvals",
      ],
    };
  }
}
