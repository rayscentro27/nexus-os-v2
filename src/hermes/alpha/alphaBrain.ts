import { AlphaLocalMemory } from "./alphaMemory";
import { runAlphaProvider } from "./alphaProviderRouter";
import { AlphaResearchFileAdapter } from "./alphaResearchFileAdapter";
import { analyzeOpportunity } from "./opportunityDesk";
import { draftMarketingAsset } from "./marketingAssetStudio";
import { analyzeTradingStrategy } from "./tradingResearchLab";
import { createRayReviewProposal } from "./rayReviewProposal";
import { runNoSupabaseGuard } from "./noSupabaseGuard";
import { scoreAlphaObjective } from "./alphaScoring";
import type { AlphaLane, AlphaNode, AlphaRequest, AlphaResponse } from "./alphaTypes";

const NODES: AlphaNode[] = [
  "classify_objective", "select_lane", "gather_context", "score_or_structure",
  "create_recommendation", "create_report_or_proposal", "write_alpha_memory", "return_response",
];

export function classifyAlphaLane(objective: string): AlphaLane {
  const text = objective.toLowerCase();
  if (/strategy|backtest|trade|drawdown|forex|market/.test(text)) return "trading_research";
  if (/landing|newsletter|facebook|social|campaign|creative|image|marketing/.test(text)) return "marketing_asset";
  if (/affiliate|referral|commission/.test(text)) return "affiliate_offer";
  if (/opportunity|monetiz|offer|business idea|revenue/.test(text)) return "business_opportunity";
  if (/research|source|document|transcript|youtube|repo/.test(text)) return "research_intake";
  return "general_strategy";
}

export class HermesAlphaBrain {
  private memory = new AlphaLocalMemory();
  private files = new AlphaResearchFileAdapter();

  run(request: AlphaRequest): AlphaResponse {
    runNoSupabaseGuard();
    const objective = request.objective.trim();
    if (!objective) throw new Error("Alpha requires Ray's objective.");
    const lane = request.requestedLane || classifyAlphaLane(objective);
    const sourceMode = request.sourceMode || "brain_only";
    const acceptedArtifacts = this.files.accept(request.artifacts || []);
    const provider = runAlphaProvider(objective);

    let recommendation: string;
    let nextExperiment: string;
    let risk: "low" | "medium" | "high" = "medium";
    let answer: string;
    let score = scoreAlphaObjective(lane, objective);

    if (lane === "business_opportunity" || lane === "affiliate_offer") {
      const result = analyzeOpportunity(objective);
      ({ recommendation, nextExperiment, risk, score } = result);
      answer = `Business opportunity research is structured for a reversible manual test. ${recommendation}`;
    } else if (lane === "marketing_asset") {
      const result = draftMarketingAsset(objective);
      score = result.score;
      recommendation = "Keep the asset draft-only, separate the audience/brand, and route exact copy through Ray Review.";
      nextExperiment = "Draft one audience-specific variant and define the manual success metric.";
      answer = `${result.title} prepared as draft-only. Publishing and sending are disabled.`;
    } else if (lane === "trading_research") {
      const result = analyzeTradingStrategy(objective);
      score = result.score;
      recommendation = "Continue only as offline strategy research and backtest planning; reject execution until guardrails and evidence pass.";
      nextExperiment = result.nextExperiment;
      risk = "high";
      answer = "Trading strategy intake completed as research/demo planning only. No broker connection or trade execution is available.";
    } else {
      recommendation = "Structure the objective, collect allowed evidence, score it, and propose the smallest reversible test.";
      nextExperiment = "Add one allowed research artifact or define one measurable manual experiment.";
      risk = "low";
      answer = `${provider.text}. ${acceptedArtifacts.length} allowed artifact(s) accepted.`;
    }

    const proposal = createRayReviewProposal({ lane, objective, recommendation, risk });
    this.memory.write({ id: `alpha-${this.memory.list().length + 1}`, createdAt: new Date().toISOString(), lane, objective, recommendation, assumptions: ["Phase 1 uses mock reasoning and allowed local artifacts only."], sourceMode });
    return {
      answer, lane, confidence: acceptedArtifacts.length ? 0.72 : 0.58,
      assumptions: ["Phase 1 is disabled and mock/offline.", "No current public research was fetched by the runtime."],
      nextExperiment, risk, recommendation,
      rayReviewDraftOption: `${proposal.title} — ${proposal.status}`,
      sourceMode, noSupabaseUsed: true, provider: "mock", nodesVisited: NODES,
      score, memoryWritten: true, externalActionPerformed: false,
    };
  }

  listMemory() {
    return this.memory.list();
  }
}
