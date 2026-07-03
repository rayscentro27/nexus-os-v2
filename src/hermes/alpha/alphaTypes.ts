export const ALPHA_SOURCE_ORDER = [
  "ray_objective",
  "alpha_brain_instructions",
  "model_reasoning",
  "public_research_or_uploaded_documents",
  "alpha_local_memory",
  "lane_scoring_frameworks",
  "future_backtest_or_demo_results",
  "recommendation_report_or_proposal",
] as const;

export type AlphaLane =
  | "research_intake"
  | "business_opportunity"
  | "marketing_asset"
  | "affiliate_offer"
  | "trading_research"
  | "general_strategy";

export type AlphaNode =
  | "classify_objective"
  | "select_lane"
  | "gather_context"
  | "score_or_structure"
  | "create_recommendation"
  | "create_report_or_proposal"
  | "write_alpha_memory"
  | "return_response";

export type AlphaProvider = "mock" | "ollama_local" | "ollama_cloud" | "openrouter" | "hosted_custom";
export type AlphaSourceMode = "brain_only" | "local_files" | "public_research" | "uploaded_documents";

export interface AlphaRequest {
  objective: string;
  requestedLane?: AlphaLane;
  sourceMode?: AlphaSourceMode;
  artifacts?: AlphaResearchArtifact[];
}

export interface AlphaResearchArtifact {
  id: string;
  title: string;
  kind: "report" | "notebook_export" | "youtube_metadata" | "transcript" | "manual_note" | "strategy_note" | "opportunity" | "marketing_research";
  path: string;
  summary?: string;
}

export interface AlphaScore {
  total: number;
  dimensions: Record<string, number>;
  rationale: string[];
}

export interface AlphaResponse {
  answer: string;
  lane: AlphaLane;
  confidence: number;
  assumptions: string[];
  nextExperiment: string;
  risk: "low" | "medium" | "high";
  recommendation: string;
  rayReviewDraftOption: string;
  sourceMode: AlphaSourceMode;
  noSupabaseUsed: true;
  provider: "mock";
  nodesVisited: AlphaNode[];
  score?: AlphaScore;
  memoryWritten: boolean;
  externalActionPerformed: false;
}

export interface AlphaMemoryEntry {
  id: string;
  createdAt: string;
  lane: AlphaLane;
  objective: string;
  recommendation: string;
  assumptions: string[];
  sourceMode: AlphaSourceMode;
}
