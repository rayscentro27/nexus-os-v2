import type { AlphaResearchArtifact } from "./alphaTypes";

export const ALPHA_RESEARCH_FILE_POLICY = Object.freeze({
  allowedDirectories: [
    "hermes_alpha/research_inbox/",
    "reports/hermes_alpha/",
    "reports/manual_publish/",
    "data/exports/notebooklm/",
    "data/sources/notebooklm_exports/",
    "data/sources/youtube_transcripts/",
    "hermes_alpha/evaluations/fixtures/",
  ],
  allowedExtensions: [".md", ".txt", ".json", ".csv"],
  rejectedExtensions: [".env", ".key", ".pem", ".p12", ".db", ".sqlite", ".sql", ".exe", ".dmg", ".zip"],
  maxFileSizeBytes: 1_000_000,
});

export type AlphaArtifactCategory = "youtube_research" | "notebooklm_export" | "transcript" | "monetization_report" | "repo_tool_research" | "trading_strategy_note" | "manual_note" | "marketing_research";
export type AlphaArtifactRoute = "online_research" | "business_opportunity" | "affiliate_offer" | "landing_page" | "newsletter" | "social_content" | "trading_research" | "ray_review_draft";

export interface AlphaFileCandidate extends AlphaResearchArtifact {
  sizeBytes: number;
  category: AlphaArtifactCategory;
  tags?: string[];
}

export interface AlphaFileValidationResult {
  artifact: AlphaFileCandidate;
  accepted: boolean;
  route: AlphaArtifactRoute;
  evidenceQuality: "mock" | "unverified" | "curated_local";
  reasons: string[];
  draftOnly: true;
  prohibitedAdaptersTouched: false;
}

const BLOCKED_SEGMENTS = ["client", ".env", "secret", "credential", "service-role", "production", "private"];

function extension(path: string): string {
  const dot = path.lastIndexOf(".");
  return dot >= 0 ? path.slice(dot).toLowerCase() : "";
}

export function isAlphaResearchArtifactFilename(path: string): boolean {
  const normalized = path.toLowerCase().replaceAll("\\", "/");
  const name = normalized.slice(normalized.lastIndexOf("/") + 1);
  return name !== "readme.md" && name !== ".gitkeep" && ALPHA_RESEARCH_FILE_POLICY.allowedExtensions.includes(extension(normalized));
}

function routeArtifact(candidate: AlphaFileCandidate): AlphaArtifactRoute {
  const text = `${candidate.title} ${(candidate.tags || []).join(" ")} ${candidate.category}`.toLowerCase();
  if (/execute|publish|send|charge|place trade|order/.test(text)) return "ray_review_draft";
  if (/affiliate|referral/.test(text)) return "affiliate_offer";
  if (/landing/.test(text)) return "landing_page";
  if (/newsletter/.test(text)) return "newsletter";
  if (/social|facebook/.test(text)) return "social_content";
  if (candidate.category === "trading_strategy_note" || /trading|strategy|backtest/.test(text)) return "trading_research";
  if (candidate.category === "monetization_report" || /opportunity|monetiz|revenue|offer/.test(text)) return "business_opportunity";
  return "online_research";
}

export class AlphaResearchFileAdapter {
  validateCandidate(candidate: AlphaFileCandidate): AlphaFileValidationResult {
    const normalized = candidate.path.toLowerCase().replaceAll("\\", "/").replace(/^\.\//, "");
    const ext = extension(normalized);
    const reasons: string[] = [];
    if (!ALPHA_RESEARCH_FILE_POLICY.allowedDirectories.some((root) => normalized.startsWith(root))) reasons.push("directory_not_allowed");
    if (!ALPHA_RESEARCH_FILE_POLICY.allowedExtensions.includes(ext)) reasons.push("extension_not_allowed");
    if (ALPHA_RESEARCH_FILE_POLICY.rejectedExtensions.includes(ext)) reasons.push("rejected_file_type");
    if (candidate.sizeBytes < 0 || candidate.sizeBytes > ALPHA_RESEARCH_FILE_POLICY.maxFileSizeBytes) reasons.push("file_size_out_of_bounds");
    if (BLOCKED_SEGMENTS.some((segment) => normalized.includes(segment))) reasons.push("sensitive_path_segment");
    if (!isAlphaResearchArtifactFilename(normalized)) reasons.push("policy_document_not_artifact");
    return {
      artifact: structuredClone(candidate), accepted: reasons.length === 0, route: routeArtifact(candidate),
      evidenceQuality: normalized.includes("fixtures/") ? "mock" : "unverified",
      reasons, draftOnly: true, prohibitedAdaptersTouched: false,
    };
  }

  validate(artifact: AlphaResearchArtifact): boolean {
    return this.validateCandidate({ ...artifact, sizeBytes: 0, category: "manual_note" }).accepted;
  }

  discoverFromManifest(candidates: AlphaFileCandidate[]): AlphaFileValidationResult[] {
    return candidates.map((candidate) => this.validateCandidate(candidate));
  }

  accept(artifacts: AlphaResearchArtifact[]): AlphaResearchArtifact[] {
    return artifacts.filter((artifact) => this.validate(artifact)).map((artifact) => structuredClone(artifact));
  }
}
