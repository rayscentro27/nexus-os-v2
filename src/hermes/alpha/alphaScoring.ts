import type { AlphaLane, AlphaScore } from "./alphaTypes";

const LANE_DIMENSIONS: Record<AlphaLane, string[]> = {
  research_intake: ["relevance", "credibility", "novelty", "routing_value"],
  business_opportunity: ["revenue_potential", "speed_to_launch", "low_cost_test", "demand", "nexus_fit", "compliance_safety"],
  marketing_asset: ["audience_fit", "clarity", "proof", "cta_fit", "compliance_safety"],
  affiliate_offer: ["audience_fit", "client_value", "economics", "disclosure_readiness", "compliance_safety"],
  trading_research: ["specification_quality", "sample_plan", "risk_definition", "testability", "stability_plan"],
  general_strategy: ["impact", "feasibility", "cost_control", "reversibility", "evidence_quality"],
};

export function scoreAlphaObjective(lane: AlphaLane, objective: string): AlphaScore {
  const dimensions = Object.fromEntries(LANE_DIMENSIONS[lane].map((name, index) => [name, Math.max(40, 70 - index * 4)]));
  const values = Object.values(dimensions);
  return {
    total: Math.round(values.reduce((sum, value) => sum + value, 0) / values.length),
    dimensions,
    rationale: [`The objective is structured for the ${lane.replaceAll("_", " ")} lane.`, `Evidence is limited to the Phase 1 offline prompt and allowed artifacts: ${objective.slice(0, 80)}.`],
  };
}
