import { describe, expect, it } from "vitest";
import { ALPHA_RESEARCH_FILE_POLICY, AlphaResearchFileAdapter, type AlphaFileCandidate } from "../src/hermes/alpha/alphaResearchFileAdapter";

const base: AlphaFileCandidate = {
  id: "mock-artifact", title: "Mock general research note", kind: "manual_note",
  path: "reports/hermes_alpha/mock_note.md", sizeBytes: 100, category: "manual_note", tags: [],
};

describe("Alpha Research File Adapter v1 foundation", () => {
  it("defines bounded directories, extensions, and size", () => {
    expect(ALPHA_RESEARCH_FILE_POLICY.allowedDirectories.length).toBeGreaterThan(0);
    expect(ALPHA_RESEARCH_FILE_POLICY.allowedExtensions).toEqual([".md", ".txt", ".json", ".csv"]);
    expect(ALPHA_RESEARCH_FILE_POLICY.maxFileSizeBytes).toBe(1_000_000);
  });

  it.each([
    ["Business opportunity", "monetization_report", ["opportunity"], "business_opportunity"],
    ["Affiliate referral note", "marketing_research", ["affiliate"], "affiliate_offer"],
    ["Landing page idea", "marketing_research", ["landing"], "landing_page"],
    ["Newsletter idea", "marketing_research", ["newsletter"], "newsletter"],
    ["Facebook social idea", "marketing_research", ["social"], "social_content"],
    ["Trading strategy", "trading_strategy_note", ["backtest"], "trading_research"],
  ] as const)("routes allowed mock artifact %s", (title, category, tags, route) => {
    const result = new AlphaResearchFileAdapter().validateCandidate({ ...base, title, category, tags: [...tags] });
    expect(result.accepted).toBe(true);
    expect(result.route).toBe(route);
    expect(result.draftOnly).toBe(true);
    expect(result.prohibitedAdaptersTouched).toBe(false);
  });

  it.each([
    "../../.env",
    "reports/hermes_alpha/private_client_note.md",
    "reports/hermes_alpha/key.pem",
    "reports/hermes_alpha/export.sql",
  ])("rejects unsafe path/type %s", (path) => {
    expect(new AlphaResearchFileAdapter().validateCandidate({ ...base, path }).accepted).toBe(false);
  });

  it("rejects oversized files", () => {
    expect(new AlphaResearchFileAdapter().validateCandidate({ ...base, sizeBytes: 1_000_001 }).reasons).toContain("file_size_out_of_bounds");
  });

  it("routes risky execution language to a draft proposal only", () => {
    const result = new AlphaResearchFileAdapter().validateCandidate({ ...base, title: "Publish this campaign", tags: ["execute"] });
    expect(result.route).toBe("ray_review_draft");
    expect(result.draftOnly).toBe(true);
  });
});
