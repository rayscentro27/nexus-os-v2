import { describe, it, expect } from "vitest";
import { existsSync, readFileSync } from "fs";
import { join } from "path";

const ROOT = join(import.meta.dirname, "..");
const BLUEPRINT_PATH = join(ROOT, "reports", "nexus_research", "supabase_plan", "approval_gated_supabase_integration_blueprint.md");
const DRYRUN_PATH = join(ROOT, "reports", "nexus_research", "supabase_plan", "supabase_integration_dry_run_manifest.json");
const DRYRUN_REPORT = join(ROOT, "reports", "nexus_research", "supabase_plan", "supabase_integration_dry_run_report.md");
const RLS_AUDIT = join(ROOT, "reports", "nexus_research", "supabase_plan", "nexus_research_rls_storage_audit.md");
const TABLE_MAP = join(ROOT, "reports", "nexus_research", "supabase_plan", "nexus_research_table_mapping_plan.md");
const DATA_CLASS = join(ROOT, "reports", "nexus_research", "supabase_plan", "nexus_research_data_classification_policy.md");
const CONNECTION_PLAN = join(ROOT, "reports", "nexus_research", "supabase_plan", "nexus_research_supabase_connection_plan.md");
const ADAPTER_SRC = join(ROOT, "src", "hermes", "nexus", "nexusResearchAdapter.ts");
const RUNNER_SRC = join(ROOT, "nexus_research", "internal_test_runner", "goclearReadinessInternalTestRunner.ts");

describe("Supabase Plan — Design Only", () => {
  it("blueprint exists and is dry-run only", () => {
    expect(existsSync(BLUEPRINT_PATH)).toBe(true);
    const content = readFileSync(BLUEPRINT_PATH, "utf-8");
    expect(content).toContain("DRY RUN ONLY");
    expect(content).toContain("NOT WRITTEN TO SUPABASE");
  });

  it("dry-run manifest exists and is labeled not real client data", () => {
    expect(existsSync(DRYRUN_PATH)).toBe(true);
    const manifest = JSON.parse(readFileSync(DRYRUN_PATH, "utf-8"));
    expect(manifest.status).toContain("DRY RUN ONLY");
    expect(manifest.status).toContain("NOT REAL CLIENT DATA");
  });

  it("dry-run report exists", () => {
    expect(existsSync(DRYRUN_REPORT)).toBe(true);
    const content = readFileSync(DRYRUN_REPORT, "utf-8");
    expect(content).toContain("DRY RUN ONLY");
  });

  it("RLS audit exists and documents requirements", () => {
    expect(existsSync(RLS_AUDIT)).toBe(true);
    const content = readFileSync(RLS_AUDIT, "utf-8").toLowerCase();
    expect(content).toContain("rls");
    expect(content).toContain("tenant");
  });

  it("table mapping exists with 5 tables", () => {
    expect(existsSync(TABLE_MAP)).toBe(true);
    const content = readFileSync(TABLE_MAP, "utf-8");
    expect(content).toContain("nexus_research_artifacts");
    expect(content).toContain("nexus_research_reviews");
    expect(content).toContain("goclear_readiness_internal_tests");
    expect(content).toContain("goclear_readiness_report_drafts");
    expect(content).toContain("ray_review_research_queue");
  });

  it("data classification policy exists", () => {
    expect(existsSync(DATA_CLASS)).toBe(true);
    const content = readFileSync(DATA_CLASS, "utf-8");
    expect(content).toContain("Level 1");
    expect(content).toContain("Level 2");
    expect(content).toContain("Level 3");
    expect(content).toContain("Level 4");
  });

  it("connection plan exists", () => {
    expect(existsSync(CONNECTION_PLAN)).toBe(true);
    const content = readFileSync(CONNECTION_PLAN, "utf-8");
    expect(content).toContain("NOT APPROVED");
    expect(content).toContain("NOT LIVE");
  });
});

describe("Supabase Plan — No Live Writes", () => {
  it("no Supabase client in adapter", () => {
    const content = readFileSync(ADAPTER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
    expect(content).not.toContain("createclient");
  });

  it("no Supabase client in runner", () => {
    const content = readFileSync(RUNNER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
    expect(content).not.toContain("createclient");
  });

  it("dry-run manifest has no real client data", () => {
    const manifest = JSON.parse(readFileSync(DRYRUN_PATH, "utf-8"));
    const jsonStr = JSON.stringify(manifest).toLowerCase();
    expect(jsonStr).toContain("not real client data");
    expect(jsonStr).not.toContain("actual client data");
    expect(jsonStr).not.toContain("production client data");
  });
});

describe("Supabase Plan — tenant_id/RLS Requirements", () => {
  it("table mapping documents tenant_id", () => {
    const content = readFileSync(TABLE_MAP, "utf-8");
    expect(content).toContain("tenant_id");
    expect(content).toContain("auth.users");
  });

  it("RLS audit documents RLS requirements", () => {
    const content = readFileSync(RLS_AUDIT, "utf-8");
    expect(content).toContain("ENABLE ROW LEVEL SECURITY");
    expect(content).toContain("tenant_isolation");
  });

  it("client-facing approval flag is required", () => {
    const content = readFileSync(TABLE_MAP, "utf-8");
    expect(content).toContain("client_facing_allowed");
    expect(content).toContain("ray_review_status");
  });

  it("draft/approved states are documented", () => {
    const content = readFileSync(TABLE_MAP, "utf-8");
    expect(content).toContain("pending");
    expect(content).toContain("approved");
    expect(content).toContain("rejected");
  });
});
