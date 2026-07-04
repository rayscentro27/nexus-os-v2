import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { ALPHA_SOURCE_ORDER } from "../src/hermes/alpha/alphaTypes";
import { ALPHA_ENV_DEFAULTS } from "../src/hermes/alpha/alphaSafety";
import { runNoSupabaseGuard } from "../src/hermes/alpha/noSupabaseGuard";

const alphaDir = join(process.cwd(), "src/hermes/alpha");
const sources = readdirSync(alphaDir).filter((name) => name.endsWith(".ts")).map((name) => ({ name, text: readFileSync(join(alphaDir, name), "utf8") }));

describe("Hermes Alpha Phase 1 connection guard", () => {
  it("has no Supabase imports, client creation, client table access, or Nexus source-authority tables", () => {
    for (const source of sources) {
      expect(source.text, source.name).not.toMatch(/(?:from|import\s*\()\s*["'](?:@supabase|[^"']*supabaseClient)/i);
      expect(source.text, source.name).not.toMatch(/\bcreateClient\s*\(/);
      expect(source.text, source.name).not.toMatch(/client_profiles/i);
      expect(source.text, source.name).not.toMatch(/task_requests|\bapprovals\b/i);
      expect(source.text, source.name).not.toMatch(/VITE_SUPABASE|SUPABASE_URL|SERVICE_ROLE/i);
    }
  });

  it("contains no Oanda order execution", () => {
    for (const source of sources) {
      expect(source.text, source.name).not.toMatch(/api-fx(?:practice|trade)|\/orders\b|createOrder|placeOrder/i);
    }
  });

  it("contains no Research Vault connector or direct browser provider call", () => {
    for (const source of sources) {
      expect(source.text, source.name).not.toMatch(/research.?vault.*(?:connect|query|read)/i);
      if (source.name !== "alphaProviderBridge.ts") expect(source.text, source.name).not.toMatch(/(?:fetch|axios)\s*\(/i);
      expect(source.text, source.name).not.toMatch(/\.chat\s*\(|\.generate\s*\(|invokeModel|openai\s*\(/i);
    }
    const bridge = sources.find((source) => source.name === "alphaProviderBridge.ts")!.text;
    expect(bridge).toMatch(/fetch\('\/api\/alpha\/(?:status|chat)/);
    expect(bridge).not.toMatch(/https?:\/\/|GROQ_API_KEY|OPENROUTER_API_KEY|Bearer /);
  });

  it("defaults every future connection and execution flag to false", () => {
    expect(ALPHA_ENV_DEFAULTS.HERMES_ALPHA_ENABLED).toBe(false);
    expect(ALPHA_ENV_DEFAULTS.HERMES_ALPHA_ALLOW_SUPABASE).toBe(false);
    expect(ALPHA_ENV_DEFAULTS.HERMES_ALPHA_ALLOW_OANDA).toBe(false);
    expect(ALPHA_ENV_DEFAULTS.HERMES_ALPHA_ALLOW_LIVE_TRADING).toBe(false);
    expect(ALPHA_ENV_DEFAULTS.HERMES_ALPHA_ALLOW_EXTERNAL_MODEL).toBe(false);
    expect(ALPHA_ENV_DEFAULTS.HERMES_ALPHA_MAX_DAILY_COST_USD).toBe(0);
  });

  it("keeps the Phase 1 source order connection-free", () => {
    expect(ALPHA_SOURCE_ORDER.join(" ")).not.toMatch(/supabase|database|client data/i);
    expect(runNoSupabaseGuard()).toMatchObject({ passed: true, noSupabaseUsed: true, connectionEnabled: false, productionAccess: false });
  });
});
