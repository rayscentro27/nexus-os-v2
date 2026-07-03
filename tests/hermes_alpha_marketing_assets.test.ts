import { describe, expect, it } from "vitest";
import { HermesAlphaBrain } from "../src/hermes/alpha/alphaBrain";
import { draftMarketingAsset } from "../src/hermes/alpha/marketingAssetStudio";

describe("Hermes Alpha Marketing Asset Studio", () => {
  it("creates drafts but cannot publish or send", () => {
    const draft = draftMarketingAsset("Draft a Facebook post for a manual readiness review", "facebook_post");
    expect(draft.status).toBe("draft_only");
    expect(draft.mayPublish).toBe(false);
    expect(draft.maySend).toBe(false);
    expect(draft.rayReviewRequired).toBe(true);
  });

  it("routes marketing objectives to the separate marketing lane", () => {
    const result = new HermesAlphaBrain().run({ objective: "Draft a landing page and newsletter campaign" });
    expect(result.lane).toBe("marketing_asset");
    expect(result.answer).toMatch(/draft-only/i);
    expect(result.answer).toMatch(/publishing and sending are disabled/i);
  });
});
