import { scoreAlphaObjective } from "./alphaScoring";

export type MarketingAssetKind = "landing_page" | "newsletter" | "facebook_post" | "social_post" | "image_prompt" | "campaign";

export function draftMarketingAsset(objective: string, kind: MarketingAssetKind = "campaign") {
  const templates: Record<MarketingAssetKind, string> = {
    landing_page: `Headline: A clearer way to evaluate ${objective.trim()}\nSubhead: Review the evidence, risks, and next experiment before acting.\nCTA: Request Ray Review of this draft.`,
    newsletter: `Subject: Alpha research brief — evaluation only\nSummary: ${objective.trim()}\nNext step: Review the evidence and choose one controlled experiment.`,
    facebook_post: `Evaluation-only draft: ${objective.trim()}\nWhat is the smallest useful test? Review before publishing.`,
    social_post: `Research note: ${objective.trim()}\nDraft only. Evidence and approval required.`,
    image_prompt: `Create a clean editorial concept illustrating: ${objective.trim()}. No logos, testimonials, performance claims, or real people. Include space for an evaluation-only label.`,
    campaign: `Audience hypothesis and draft campaign concept for: ${objective.trim()}`,
  };
  return {
    kind,
    status: "draft_only" as const,
    title: `Alpha ${kind.replaceAll("_", " ")} draft`,
    content: templates[kind],
    score: scoreAlphaObjective("marketing_asset", objective),
    mayPublish: false,
    maySend: false,
    rayReviewRequired: true,
  };
}
