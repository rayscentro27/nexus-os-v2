import fixtureData from "../../../hermes_alpha/evaluations/fixtures/phase1_fixtures.json";
import { HermesAlphaBrain } from "./alphaBrain";
import { draftMarketingAsset, type MarketingAssetKind } from "./marketingAssetStudio";
import { createRayReviewProposal } from "./rayReviewProposal";
import { createBacktestPlan, createTradingRiskReview } from "./tradingResearchLab";
import type { AlphaLane } from "./alphaTypes";

export type AlphaEvaluationCategory = "business_opportunity" | "affiliate_offer" | "landing_page" | "newsletter" | "social_post" | "image_prompt" | "trading_research" | "backtest_plan" | "trading_risk_review" | "ray_review_proposal" | "safety_refusal";

export interface AlphaEvaluationFixture {
  name: string;
  category: AlphaEvaluationCategory;
  objective: string;
  expectedRoute: AlphaLane;
  evaluationOnly: true;
}

export interface AlphaEvaluationResult {
  fixtureName: string;
  inputCategory: AlphaEvaluationCategory;
  routeSelected: AlphaLane;
  scoreOrRating: number | "blocked";
  recommendation: string;
  draftOutputPath: string | null;
  safetyStatus: "passed" | "blocked";
  draftOnly: true;
  prohibitedAdaptersTouched: false;
  pass: boolean;
  reportPath: string;
  outputPreview: string;
  mockEvaluationOnly: true;
}

export const ALPHA_PHASE_1_FIXTURES = fixtureData as AlphaEvaluationFixture[];

const marketingKinds: Partial<Record<AlphaEvaluationCategory, MarketingAssetKind>> = {
  landing_page: "landing_page", newsletter: "newsletter", social_post: "facebook_post", image_prompt: "image_prompt",
};

export function runAlphaEvaluation(fixture: AlphaEvaluationFixture): AlphaEvaluationResult {
  const brain = new HermesAlphaBrain();
  const response = brain.run({ objective: fixture.objective });
  let preview = response.answer;
  let outputPath: string | null = null;
  if (marketingKinds[fixture.category]) {
    const asset = draftMarketingAsset(fixture.objective, marketingKinds[fixture.category]);
    preview = asset.content;
    outputPath = "hermes_alpha/evaluations/results/phase1_results.json";
  } else if (fixture.category === "backtest_plan") {
    preview = createBacktestPlan(fixture.objective).steps.join("; ");
    outputPath = "hermes_alpha/evaluations/results/phase1_results.json";
  } else if (fixture.category === "trading_risk_review") {
    preview = createTradingRiskReview(fixture.objective).recommendation;
    outputPath = "hermes_alpha/evaluations/results/phase1_results.json";
  } else if (fixture.category === "ray_review_proposal") {
    preview = createRayReviewProposal({ lane: response.lane, objective: fixture.objective, recommendation: response.recommendation, risk: response.risk }).status;
    outputPath = "hermes_alpha/evaluations/results/phase1_results.json";
  }
  const expectedBlocked = fixture.category === "safety_refusal";
  const pass = response.lane === fixture.expectedRoute && (expectedBlocked ? response.safetyStatus === "blocked" : response.safetyStatus === "passed");
  return {
    fixtureName: fixture.name, inputCategory: fixture.category, routeSelected: response.lane,
    scoreOrRating: response.safetyStatus === "blocked" ? "blocked" : response.score?.total || 0,
    recommendation: response.recommendation, draftOutputPath: outputPath,
    safetyStatus: response.safetyStatus, draftOnly: true, prohibitedAdaptersTouched: false,
    pass, reportPath: "reports/hermes_alpha/alpha_phase_1_evaluation_harness_report.md",
    outputPreview: preview, mockEvaluationOnly: true,
  };
}

export function runAlphaPhase1Evaluations(): AlphaEvaluationResult[] {
  return ALPHA_PHASE_1_FIXTURES.map(runAlphaEvaluation);
}

export function summarizeAlphaEvaluations(results = runAlphaPhase1Evaluations()) {
  return {
    total: results.length,
    passed: results.filter((result) => result.pass).length,
    failed: results.filter((result) => !result.pass).length,
    blocked: results.filter((result) => result.safetyStatus === "blocked").length,
    allDraftOnly: results.every((result) => result.draftOnly),
    prohibitedAdaptersTouched: results.some((result) => result.prohibitedAdaptersTouched),
    mockEvaluationOnly: true as const,
  };
}
