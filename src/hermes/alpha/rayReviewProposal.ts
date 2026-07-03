import type { AlphaLane } from "./alphaTypes";

export function createRayReviewProposal(input: { lane: AlphaLane; objective: string; recommendation: string; risk: string }) {
  return {
    status: "conversation_draft_only" as const,
    title: `Hermes Alpha proposal: ${input.objective.slice(0, 80)}`,
    lane: input.lane,
    recommendation: input.recommendation,
    risk: input.risk,
    decisionNeeded: "approve, revise, or reject the proposed experiment",
    externalActionAuthorized: false,
    saved: false,
    submitted: false,
  };
}
