import { scoreAlphaObjective } from "./alphaScoring";

export type MarketingAssetKind = "landing_page" | "newsletter" | "facebook_post" | "social_post" | "image_prompt" | "campaign";

export function draftMarketingAsset(objective: string, kind: MarketingAssetKind = "campaign") {
  return {
    kind,
    status: "draft_only" as const,
    title: `Alpha ${kind.replaceAll("_", " ")} draft`,
    content: `Audience hypothesis and draft concept for: ${objective.trim()}`,
    score: scoreAlphaObjective("marketing_asset", objective),
    mayPublish: false,
    maySend: false,
    rayReviewRequired: true,
  };
}
