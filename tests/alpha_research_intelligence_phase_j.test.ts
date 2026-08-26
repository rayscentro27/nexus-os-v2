import { describe, expect, it } from "vitest";
import { createResearchPlan, detectSensitiveResearchPayload, executeAlphaResearch, validateEvidenceForClaim, validateResearchJob, type AcceptedEvidence } from "../src/hermes/alpha/alphaResearchIntelligence";

const evidence: AcceptedEvidence[] = [
  { evidence_id: "ev-official", artifact_ref: "data/runtime/evidence_ingestion/artifacts/ev-official.json", original_source: "https://docs.example.org/current", source_type: "public_url", retrieved_at: new Date().toISOString(), text: "Official public documentation states the capability is available.", quality: "AUTHORITATIVE" },
  { evidence_id: "ev-secondary", artifact_ref: "data/runtime/evidence_ingestion/artifacts/ev-secondary.json", original_source: "https://example.com/analysis", source_type: "public_url", retrieved_at: new Date().toISOString(), text: "A secondary source describes the market context.", quality: "SECONDARY" },
];

describe("Alpha Phase J research intelligence", () => {
  it("validates a versioned bounded tenant-aware job", () => {
    const job = validateResearchJob({ objective: "Compare public technology tools", research_type: "TECHNOLOGY_RESEARCH", tenant_context: { scope: "founder_admin", tenant_id: null } });
    expect(job.schema_version).toBe("nexus.alpha-research-job.v1"); expect(job.limits.maxSources).toBe(10); expect(job.source_policy.evidence_required).toBe(true);
    expect(() => validateResearchJob({ objective: "", research_type: "MARKET_RESEARCH" })).toThrow("objective_required");
    expect(() => validateResearchJob({ objective: "x", research_type: "NOT_A_TYPE" as never })).toThrow("invalid_research_type");
  });
  it("blocks PII, credentials, and excessive bounds", () => {
    expect(detectSensitiveResearchPayload({ objective: "Use client SSN 123-45-6789" })).toBe(true);
    expect(() => validateResearchJob({ objective: "Read client credit report", research_type: "MARKET_RESEARCH" })).toThrow("SAFETY_BLOCKED");
    expect(() => validateResearchJob({ objective: "x", research_type: "MARKET_RESEARCH", limits: { maxSources: 51, maxEvidenceJobs: 1, maxModelCalls: 1, maxRuntimeMs: 1, maxOutputChars: 1 } })).toThrow("limits_exceed_policy");
  });
  it("creates a bounded plan and structured pack/report/receipt", () => {
    const job = validateResearchJob({ objective: "Compare public competitors", research_type: "COMPETITOR_RESEARCH", limits: { maxSources: 1, maxEvidenceJobs: 1, maxModelCalls: 1, maxRuntimeMs: 1000, maxOutputChars: 5000 } });
    const plan = createResearchPlan(job); expect(plan.stopping_criteria.join(" ")).toMatch(/source|evidence|runtime/i);
    const result = executeAlphaResearch(job, evidence, { remoteJobs: 1, provider: "none" });
    expect(result.pack.schema_version).toBe("nexus.alpha-research-pack.v1"); expect(result.pack.status).toBe("COMPLETE"); expect(result.pack.claims[0].evidence_refs).toEqual(["ev-official"]); expect(result.report).toContain("Research Limits"); expect(result.receipt.schema_version).toBe("nexus.alpha-research-receipt.v1");
  });
  it("preserves honest insufficient evidence and rejects unsupported sourced claims", () => {
    const result = executeAlphaResearch({ objective: "Find public opportunities", research_type: "BUSINESS_OPPORTUNITY_RESEARCH" }, []);
    expect(result.pack.status).toBe("INSUFFICIENT_EVIDENCE"); expect(result.pack.unknowns[0]).toMatch(/No accepted evidence/);
    expect(validateEvidenceForClaim({ claim: "unsupported", claim_type: "DIRECT_EVIDENCE", confidence: "MEDIUM", evidence_refs: [], source_count: 0, source_quality: [], freshness: "UNKNOWN", contradictions: [], notes: [] })).toBe(false);
    expect(validateEvidenceForClaim({ claim: "unknown", claim_type: "UNKNOWN", confidence: "UNSUPPORTED", evidence_refs: [], source_count: 0, source_quality: [], freshness: "UNKNOWN", contradictions: [], notes: [] })).toBe(true);
  });
  it("keeps recommendations and opportunities advisory-only", () => {
    const result = executeAlphaResearch({ objective: "Research trading tools", research_type: "TRADING_RESEARCH" }, evidence);
    expect(result.pack.opportunities).toEqual([]); expect(result.report).toContain("advisory"); expect(result.receipt.remote_worker_usage.capability).toBe("none");
  });
});
