import { describe, it, expect, beforeAll } from "vitest";
import { existsSync, readFileSync } from "fs";
import { join } from "path";

const ROOT = join(import.meta.dirname, "..");
const RUNNER_SRC = join(ROOT, "nexus_research", "internal_test_runner", "goclearReadinessInternalTestRunner.ts");
const BUILDER_SRC = join(ROOT, "nexus_research", "internal_test_runner", "goclearReadinessReportBuilder.ts");
const ADAPTER_SRC = join(ROOT, "src", "hermes", "nexus", "nexusResearchAdapter.ts");
const ALPHA_ADAPTER = join(ROOT, "src", "hermes", "alpha", "alphaResearchFileAdapter.ts");
const SMOKE_RUN = join(ROOT, "reports", "nexus_research", "final_foundation", "goclear_local_internal_workflow_smoke_run.md");
const PREFLIGHT = join(ROOT, "reports", "nexus_research", "final_foundation", "goclear_readiness_foundation_preflight.md");

describe("Local Internal Workflow — Guards", () => {
  it("runner does not connect Supabase", () => {
    const content = readFileSync(RUNNER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
    expect(content).not.toContain("createclient");
  });

  it("builder does not connect Supabase", () => {
    const content = readFileSync(BUILDER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
    expect(content).not.toContain("createclient");
  });

  it("adapter does not connect Supabase", () => {
    const content = readFileSync(ADAPTER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
  });

  it("Alpha adapter does not connect Supabase", () => {
    if (existsSync(ALPHA_ADAPTER)) {
      const content = readFileSync(ALPHA_ADAPTER, "utf-8").toLowerCase();
      expect(content).not.toContain("supabase");
    }
  });

  it("no Oanda import in runner", () => {
    const content = readFileSync(RUNNER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("oanda");
  });

  it("no external provider call in runner", () => {
    const content = readFileSync(RUNNER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("fetch(");
    expect(content).not.toContain("axios");
  });

  it("no send/publish/charge/trade in runner", () => {
    const content = readFileSync(RUNNER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("send_email");
    expect(content).not.toContain("publish_post");
    expect(content).not.toContain("charge_payment");
    expect(content).not.toContain("execute_trade");
  });

  it("no production mutation in runner", () => {
    const content = readFileSync(RUNNER_SRC, "utf-8").toLowerCase();
    expect(content).not.toContain("delete_all");
    expect(content).not.toContain("drop_table");
  });

  it("smoke run report exists and documents safety", () => {
    expect(existsSync(SMOKE_RUN)).toBe(true);
    const content = readFileSync(SMOKE_RUN, "utf-8");
    expect(content).toContain("No Supabase writes");
    expect(content).toContain("No client data used");
    expect(content).toContain("draft-only");
  });

  it("preflight exists and confirms safety", () => {
    expect(existsSync(PREFLIGHT)).toBe(true);
    const content = readFileSync(PREFLIGHT, "utf-8");
    expect(content).toContain("Supabase disconnected");
    expect(content).toContain("Client data disconnected");
  });
});
