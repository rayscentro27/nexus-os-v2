import { scoreAlphaObjective } from "./alphaScoring";

export function analyzeOpportunity(objective: string) {
  const score = scoreAlphaObjective("business_opportunity", objective);
  return {
    score,
    recommendation: "Run a reversible, zero-to-low-cost demand test before building or buying infrastructure.",
    nextExperiment: "Draft one offer, one audience hypothesis, one proof requirement, and one manual conversion test for Ray Review.",
    risk: score.dimensions.compliance_safety < 60 ? "high" as const : "medium" as const,
  };
}
