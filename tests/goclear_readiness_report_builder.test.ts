import { describe, it, expect, beforeAll } from "vitest";
import { existsSync, readFileSync, readdirSync } from "fs";
import { join } from "path";
import {
  generateAllReports,
  writeAllReports,
  type InternalReadinessReport,
} from "../nexus_research/internal_test_runner/goclearReadinessReportBuilder";

const ROOT = join(import.meta.dirname, "..");
const REPORTS_DIR = join(ROOT, "reports", "nexus_research", "internal_test_runner", "readiness_reports");
const RUNNER_SRC = join(ROOT, "nexus_research", "internal_test_runner", "goclearReadinessInternalTestRunner.ts");
const BUILDER_SRC = join(ROOT, "nexus_research", "internal_test_runner", "goclearReadinessReportBuilder.ts");
const ADAPTER_SRC = join(ROOT, "src", "hermes", "nexus", "nexusResearchAdapter.ts");
const FIXTURES_DIR = join(ROOT, "nexus_research", "internal_test_runner", "fixtures");

let reports: InternalReadinessReport[];

beforeAll(() => {
  reports = generateAllReports();
});

describe("Report Builder — Internal Readiness Reports", () => {
  it("creates internal readiness reports for all profiles", () => {
    expect(reports.length).toBe(3);
    for (const r of reports) {
      expect(r.profile_id).toMatch(/^TEST-\d+$/);
      expect(r.cover_summary).toBeDefined();
      expect(r.credit_utilization_readiness).toBeDefined();
      expect(r.business_setup_readiness).toBeDefined();
    }
  });

  it("labels all reports internal/draft/Ray Review required", () => {
    for (const r of reports) {
      expect(r.report_label).toContain("INTERNAL DRAFT");
      expect(r.report_label).toContain("NOT CLIENT-FACING");
      expect(r.report_label).toContain("RAY REVIEW REQUIRED");
    }
  });

  it("does not make guarantees", () => {
    for (const r of reports) {
      const allText = [
        r.cover_summary, r.credit_utilization_readiness,
        r.business_setup_readiness, r.fundability_preparation,
        ...r.compliance_cautions, ...r.internal_admin_notes,
      ].join(" ").toLowerCase();
      expect(allText).not.toContain("we guarantee");
      expect(allText).not.toContain("guaranteed approval");
      expect(allText).not.toContain("100% approval");
    }
  });

  it("does not produce approved client-facing report", () => {
    for (const r of reports) {
      expect(r.report_label).toContain("NOT CLIENT-FACING");
      expect(r.next_internal_step).toContain("Ray should review");
    }
  });

  it("includes blocked actions", () => {
    for (const r of reports) {
      expect(r.blocked_actions.length).toBeGreaterThan(0);
      expect(r.blocked_actions).toContain("no_send");
      expect(r.blocked_actions).toContain("no_publish");
      expect(r.blocked_actions).toContain("no_charge");
      expect(r.blocked_actions).toContain("no_trade");
      expect(r.blocked_actions).toContain("no_guaranteed_approvals");
    }
  });

  it("includes compliance cautions", () => {
    for (const r of reports) {
      expect(r.compliance_cautions.length).toBeGreaterThan(0);
      expect(r.compliance_cautions.some(c => c.includes("draft-only"))).toBe(true);
    }
  });
});

describe("Report Builder — No Supabase / No Client Data", () => {
  it("report builder source has no Supabase", () => {
    const content = readFileSync(BUILDER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
    expect(content).not.toContain("createclient");
  });

  it("report builder source has no client data", () => {
    const content = readFileSync(BUILDER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("real client");
    expect(content).not.toContain("production client");
  });

  it("runner source has no Supabase", () => {
    const content = readFileSync(RUNNER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
  });

  it("adapter source has no Supabase", () => {
    const content = readFileSync(ADAPTER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
  });
});

describe("Report Builder — Fixture Safety", () => {
  it("all fixture profiles are hypothetical", () => {
    const files = readdirSync(FIXTURES_DIR).filter(f => f.endsWith(".json"));
    for (const f of files) {
      const content = readFileSync(join(FIXTURES_DIR, f), "utf-8");
      expect(content).toContain("HYPOTHETICAL INTERNAL TEST PROFILE");
      expect(content).toContain("NOT A REAL CLIENT");
    }
  });

  it("no real PII in fixtures", () => {
    const files = readdirSync(FIXTURES_DIR).filter(f => f.endsWith(".json"));
    for (const f of files) {
      const content = readFileSync(join(FIXTURES_DIR, f), "utf-8");
      expect(content).not.toMatch(/\d{3}-\d{2}-\d{4}/);
      expect(content).not.toContain("@gmail.com");
      expect(content).not.toContain("@yahoo.com");
    }
  });
});

describe("Report Builder — File Generation", () => {
  it("writes readiness reports to disk", () => {
    writeAllReports(reports);
    expect(existsSync(join(REPORTS_DIR, "starter_profile_internal_readiness_report.md"))).toBe(true);
    expect(existsSync(join(REPORTS_DIR, "improving_profile_internal_readiness_report.md"))).toBe(true);
    expect(existsSync(join(REPORTS_DIR, "stronger_profile_internal_readiness_report.md"))).toBe(true);
    expect(existsSync(join(REPORTS_DIR, "readiness_report_builder_summary.md"))).toBe(true);
  });
});
