import { describe, expect, it } from "vitest";
import { HermesAlphaBrain } from "../src/hermes/alpha/alphaBrain";
import { handleHermesMessage } from "../src/lib/hermesBrainPipeline";

describe("Hermes Alpha Brain v1", () => {
  it("answers a business opportunity objective without becoming local-report-first", () => {
    const result = new HermesAlphaBrain().run({ objective: "Evaluate a low-cost bookkeeping service business opportunity" });
    expect(result.lane).toBe("business_opportunity");
    expect(result.noSupabaseUsed).toBe(true);
    expect(result.sourceMode).toBe("brain_only");
    expect(result.answer).not.toMatch(/supabase|local report/i);
    expect(result.nextExperiment).toMatch(/manual|draft/i);
    expect(result.nodesVisited).toHaveLength(8);
  });

  it("handles trading as research/demo planning only", () => {
    const result = new HermesAlphaBrain().run({ objective: "Research and backtest a EUR/USD trend strategy" });
    expect(result.lane).toBe("trading_research");
    expect(result.answer).toMatch(/research\/demo planning only/i);
    expect(result.answer).toMatch(/no broker connection or trade execution/i);
    expect(result.risk).toBe("high");
    expect(result.externalActionPerformed).toBe(false);
  });

  it("writes only in-memory Alpha memory", () => {
    const brain = new HermesAlphaBrain();
    brain.run({ objective: "Research a small business content opportunity" });
    expect(brain.listMemory()).toHaveLength(1);
  });

  it("leaves Nexus Hermes readiness behavior unchanged", async () => {
    const response = await handleHermesMessage({ message: "is GoClear ready to launch?" });
    expect(response.route).toBe("readiness_operating_status");
    expect(response.text).toMatch(/manual-ready/i);
  });
});
