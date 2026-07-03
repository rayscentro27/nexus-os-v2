import { describe, expect, it } from "vitest";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { AlphaResearchFileAdapter, isAlphaResearchArtifactFilename } from "../src/hermes/alpha/alphaResearchFileAdapter";

const inbox = join(process.cwd(), "hermes_alpha/research_inbox");
const categories = ["youtube", "notebooklm", "transcripts", "monetization", "tools", "trading", "marketing", "manual_notes"];

describe("Hermes Alpha approved local research inbox", () => {
  it("has every approved category and policy documentation", () => {
    expect(existsSync(join(inbox, "README.md"))).toBe(true);
    const policy = readFileSync(join(inbox, "README.md"), "utf8");
    expect(policy).toMatch(/approved local Hermes Alpha research artifacts only/i);
    expect(policy).toMatch(/do not add client data/i);
    expect(policy).toMatch(/untrusted, read-only evidence/i);
    for (const category of categories) {
      expect(existsSync(join(inbox, category))).toBe(true);
      expect(existsSync(join(inbox, category, "README.md"))).toBe(true);
    }
  });

  it("treats policy-only folders as valid and artifact-empty", () => {
    for (const category of categories) {
      const artifacts = readdirSync(join(inbox, category)).filter(isAlphaResearchArtifactFilename);
      expect(artifacts, category).toEqual([]);
    }
  });

  it("does not require fake artifacts or claim ingestion on an empty manifest", () => {
    const results = new AlphaResearchFileAdapter().discoverFromManifest([]);
    expect(results).toEqual([]);
    expect(results).toHaveLength(0);
  });

  it("excludes README and placeholder files from artifact status", () => {
    expect(isAlphaResearchArtifactFilename("hermes_alpha/research_inbox/youtube/README.md")).toBe(false);
    expect(isAlphaResearchArtifactFilename("hermes_alpha/research_inbox/youtube/.gitkeep")).toBe(false);
  });
});
