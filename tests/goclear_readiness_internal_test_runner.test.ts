import { describe, it, expect, beforeAll } from "vitest";
import { existsSync, readFileSync, readdirSync } from "fs";
import { join } from "path";
import {
  loadAllProfiles,
  runAllProfiles,
  runInternalTestProfile,
  generateManifest,
  type GoClearTestProfile,
  type InternalTestResult,
} from "../nexus_research/internal_test_runner/goclearReadinessInternalTestRunner";

const ROOT = join(import.meta.dirname, "..");
const FIXTURES_DIR = join(ROOT, "nexus_research", "internal_test_runner", "fixtures");
const RESULTS_DIR = join(ROOT, "nexus_research", "internal_test_runner", "results");
const REPORTS_DIR = join(ROOT, "reports", "nexus_research", "internal_test_runner");
const ADAPTER_SRC = join(ROOT, "src", "hermes", "nexus", "nexusResearchAdapter.ts");
const RUNNER_SRC = join(ROOT, "nexus_research", "internal_test_runner", "goclearReadinessInternalTestRunner.ts");

let allResults: InternalTestResult[];
let allProfiles: GoClearTestProfile[];

beforeAll(() => {
  allProfiles = loadAllProfiles();
  allResults = runAllProfiles();
});

describe("GoClear Internal Test Runner — Profile Safety", () => {
  it("runner uses only hypothetical profiles", () => {
    for (const profile of allProfiles) {
      expect(profile.profile_type).toBe("hypothetical");
    }
  });

  it("fixture files contain hypothetical label", () => {
    const files = readdirSync(FIXTURES_DIR).filter(f => f.endsWith(".json"));
    for (const f of files) {
      const content = readFileSync(join(FIXTURES_DIR, f), "utf-8");
      expect(content).toContain("HYPOTHETICAL INTERNAL TEST PROFILE");
      expect(content).toContain("NOT A REAL CLIENT");
    }
  });

  it("profiles do not contain real names or PII", () => {
    for (const profile of allProfiles) {
      expect(profile.profile_id).toMatch(/^TEST-\d+$/);
      expect(profile.notes).not.toContain("@");
      expect(profile.notes).not.toMatch(/\d{3}-\d{2}-\d{4}/);
    }
  });
});

describe("GoClear Internal Test Runner — Category Usage", () => {
  it("runner uses only approved internal categories", () => {
    const approved = ["manual_notes", "credit_utilization", "business_setup"];
    const manifest = generateManifest(allResults);
    for (const cat of manifest.categories_used) {
      expect(approved).toContain(cat);
    }
  });

  it("runner does not use blocked categories", () => {
    const blocked = ["credit_repair", "affiliates", "compliance", "client_education", "business_funding", "grants", "lenders"];
    const manifest = generateManifest(allResults);
    for (const cat of manifest.categories_used) {
      expect(blocked).not.toContain(cat);
    }
  });
});

describe("GoClear Internal Test Runner — No Supabase", () => {
  it("runner does not require Supabase", () => {
    const content = readFileSync(RUNNER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
    expect(content).not.toContain("createclient");
    expect(content).not.toContain("from '@supabase");
  });

  it("adapter does not connect Supabase", () => {
    const content = readFileSync(ADAPTER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
    expect(content).not.toContain("createclient");
  });
});

describe("GoClear Internal Test Runner — No Client Data", () => {
  it("runner does not use client data", () => {
    const content = readFileSync(RUNNER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("real client");
    expect(content).not.toContain("production client");
    expect(content).not.toContain("actual client");
  });

  it("fixture profiles have no real financial data", () => {
    for (const profile of allProfiles) {
      expect(profile.annual_revenue).toBeGreaterThanOrEqual(0);
      expect(profile.existing_debt).toBeGreaterThanOrEqual(0);
      expect(typeof profile.credit_score_range).toBe("string");
      expect(profile.credit_score_range).not.toMatch(/^\d{3}$/);
    }
  });
});

describe("GoClear Internal Test Runner — Admin-Only Notes", () => {
  it("runner generates admin-only notes", () => {
    for (const result of allResults) {
      expect(result.admin_readiness_note.ray_review_required).toBe(true);
      expect(result.admin_readiness_note.output_label).toContain("INTERNAL TEST ONLY");
      expect(result.admin_readiness_note.output_label).toContain("NOT CLIENT-FACING");
      expect(result.admin_readiness_note.output_label).toContain("RAY REVIEW REQUIRED");
    }
  });

  it("admin notes include missing information", () => {
    const starterResult = allResults.find(r => r.profile_id === "TEST-001");
    expect(starterResult).toBeDefined();
    expect(starterResult!.admin_readiness_note.missing_information.length).toBeGreaterThan(0);
  });

  it("admin notes include risk cautions", () => {
    for (const result of allResults) {
      expect(result.admin_readiness_note.risk_compliance_cautions.length).toBeGreaterThan(0);
      expect(result.admin_readiness_note.risk_compliance_cautions.some(c => c.includes("draft-only"))).toBe(true);
    }
  });
});

describe("GoClear Internal Test Runner — Ray Review Drafts", () => {
  it("runner generates Ray Review drafts", () => {
    for (const result of allResults) {
      expect(result.ray_review_draft.title).toBeDefined();
      expect(result.ray_review_draft.profile_summary).toBeDefined();
      expect(result.ray_review_draft.recommended_next_step).toBeDefined();
      expect(result.ray_review_draft.client_facing_allowed).toBe("no");
      expect(result.ray_review_draft.approval_required).toBe(true);
    }
  });

  it("Ray Review drafts list blocked guarantees", () => {
    for (const result of allResults) {
      expect(result.ray_review_draft.blocked_guarantees.length).toBeGreaterThan(0);
      expect(result.ray_review_draft.blocked_guarantees.some(g => g.includes("funding"))).toBe(true);
      expect(result.ray_review_draft.blocked_guarantees.some(g => g.includes("score"))).toBe(true);
    }
  });
});

describe("GoClear Internal Test Runner — Output Labeling", () => {
  it("runner does not generate approved client-facing output", () => {
    for (const result of allResults) {
      expect(result.admin_readiness_note.output_label).toContain("NOT CLIENT-FACING");
      expect(result.ray_review_draft.output_label).toContain("NOT CLIENT-FACING");
      expect(result.ray_review_draft.client_facing_allowed).toBe("no");
    }
  });

  it("runner blocks guarantees", () => {
    for (const result of allResults) {
      expect(result.admin_readiness_note.blocked_actions).toContain("no_guaranteed_approvals");
      expect(result.admin_readiness_note.blocked_actions).toContain("no_score_increase_guarantees");
      expect(result.admin_readiness_note.blocked_actions).toContain("no_funding_guarantees");
      expect(result.admin_readiness_note.blocked_actions).toContain("no_deletion_guarantees");
    }
  });

  it("runner blocks automated disputes and lender applications", () => {
    for (const result of allResults) {
      expect(result.admin_readiness_note.blocked_actions).toContain("no_automated_disputes");
      expect(result.admin_readiness_note.blocked_actions).toContain("no_direct_lender_applications");
    }
  });

  it("runner blocks send/publish/charge/trade", () => {
    for (const result of allResults) {
      expect(result.admin_readiness_note.blocked_actions).toContain("no_send");
      expect(result.admin_readiness_note.blocked_actions).toContain("no_publish");
      expect(result.admin_readiness_note.blocked_actions).toContain("no_charge");
      expect(result.admin_readiness_note.blocked_actions).toContain("no_trade");
    }
  });
});

describe("GoClear Internal Test Runner — Scorecard Drafts", () => {
  it("runner outputs scorecard drafts only, not approved scores", () => {
    for (const result of allResults) {
      expect(["low", "medium", "high"]).toContain(result.readiness_scorecard.credit_utilization_readiness);
      expect(["low", "medium", "high"]).toContain(result.readiness_scorecard.business_setup_readiness);
      expect(["low", "medium", "high"]).toContain(result.readiness_scorecard.funding_readiness_preparation);
      expect(["low", "medium", "high"]).toContain(result.readiness_scorecard.documentation_readiness);
      expect(["low", "medium", "high"]).toContain(result.readiness_scorecard.client_education_need);
      expect(["low", "medium", "high"]).toContain(result.readiness_scorecard.ray_review_priority);
    }
  });
});

describe("GoClear Internal Test Runner — Profile Routing", () => {
  it("starter profile routes to high Ray Review priority", () => {
    const starter = allResults.find(r => r.profile_id === "TEST-001");
    expect(starter).toBeDefined();
    expect(starter!.readiness_scorecard.ray_review_priority).toBe("high");
  });

  it("improving profile routes to medium Ray Review priority", () => {
    const improving = allResults.find(r => r.profile_id === "TEST-002");
    expect(improving).toBeDefined();
    expect(improving!.readiness_scorecard.ray_review_priority).toBe("medium");
  });

  it("stronger profile still requires admin review before funding guidance", () => {
    const stronger = allResults.find(r => r.profile_id === "TEST-003");
    expect(stronger).toBeDefined();
    expect(stronger!.ray_review_draft.client_facing_allowed).toBe("no");
    expect(stronger!.ray_review_draft.approval_required).toBe(true);
    expect(stronger!.admin_readiness_note.ray_review_required).toBe(true);
  });
});
