import { describe, it, expect, beforeEach } from "vitest";
import { existsSync, readdirSync } from "fs";
import { join } from "path";
import {
  NexusResearchAdapter,
  NEXUS_RESEARCH_FILE_POLICY,
  validatePath,
  isApprovedInboxPath,
  detectCategory,
  routeCategory,
  detectGuaranteeFlags,
  detectComplianceFlags,
  generateArtifactId,
  resetArtifactCounter,
  computeAllowedOutputs,
  computeBlockedOutputs,
  type NexusFileCandidate,
  type NexusArtifactMetadata,
} from "../src/hermes/nexus/nexusResearchAdapter";

const ROOT = join(import.meta.dirname, "..");
const NEXUS_RESEARCH_INBOX = join(ROOT, "nexus_research", "research_inbox");
const HERMES_ALPHA_INBOX = join(ROOT, "hermes_alpha", "research_inbox");

const NEXUS_INBOX_CATEGORIES = [
  "credit_repair",
  "credit_utilization",
  "business_setup",
  "business_funding",
  "grants",
  "lenders",
  "affiliates",
  "compliance",
  "client_education",
  "manual_notes",
];

const adapter = new NexusResearchAdapter();

function makeCandidate(overrides: Partial<NexusFileCandidate> = {}): NexusFileCandidate {
  return {
    path: "nexus_research/research_inbox/credit_utilization/test_fixture.md",
    title: "Test Fixture",
    sizeBytes: 200,
    content: "# Test Credit Utilization Research\n\nThis is a test fixture for credit utilization scoring.\n\nKey points: utilization ratio affects score.",
    ...overrides,
  };
}

beforeEach(() => {
  resetArtifactCounter();
});

describe("Nexus Research Adapter — Approved Folder Enforcement", () => {
  it("adapter only reads approved Nexus Research inbox folders", () => {
    const result = adapter.processCandidate(makeCandidate());
    expect(result.parse_status).toBe("parsed");
    expect(result.canonical_path).toMatch(/^nexus_research\/research_inbox\//);
  });

  it("adapter rejects files outside approved folders", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "reports/hermes_alpha/external_note.md",
    }));
    expect(result.parse_status).toBe("rejected");
  });

  it("adapter rejects path traversal", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "nexus_research/research_inbox/../../.env",
    }));
    expect(result.parse_status).toBe("rejected");
  });

  it("adapter rejects blocked file types", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "nexus_research/research_inbox/credit_repair/secret.env",
    }));
    expect(result.parse_status).toBe("rejected");
  });

  it("adapter reads Markdown only", () => {
    expect(NEXUS_RESEARCH_FILE_POLICY.allowedExtensions).toEqual([".md"]);
    expect(NEXUS_RESEARCH_FILE_POLICY.blockedExtensions).toContain(".json");
    expect(NEXUS_RESEARCH_FILE_POLICY.blockedExtensions).toContain(".csv");
    expect(NEXUS_RESEARCH_FILE_POLICY.blockedExtensions).toContain(".pdf");
    expect(NEXUS_RESEARCH_FILE_POLICY.blockedExtensions).toContain(".js");
    expect(NEXUS_RESEARCH_FILE_POLICY.blockedExtensions).toContain(".ts");
  });
});

describe("Nexus Research Adapter — SHA-256 and Metadata", () => {
  it("adapter produces SHA-256 hash", () => {
    const result = adapter.processCandidate(makeCandidate());
    expect(result.sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(result.sha256.length).toBe(64);
  });

  it("adapter produces metadata schema with all required fields", () => {
    const result = adapter.processCandidate(makeCandidate());
    expect(result.artifact_id).toMatch(/^nexus-res-\d{8}-\d{3}$/);
    expect(result.source_path).toBeDefined();
    expect(result.canonical_path).toBeDefined();
    expect(result.filename).toBeDefined();
    expect(result.category).toBeDefined();
    expect(result.size_bytes).toBeGreaterThan(0);
    expect(result.sha256).toMatch(/^[a-f0-9]{64}$/);
    expect(result.modified_at).toBeDefined();
    expect(result.ingested_at).toBeDefined();
    expect(result.title).toBeDefined();
    expect(result.short_summary).toBeDefined();
    expect(result.evidence_quality).toBeDefined();
    expect(Array.isArray(result.compliance_flags)).toBe(true);
    expect(Array.isArray(result.guarantee_flags)).toBe(true);
    expect(typeof result.client_safe).toBe("boolean");
    expect(typeof result.admin_only).toBe("boolean");
    expect(typeof result.ray_review_required).toBe("boolean");
    expect(result.routing_target).toBeDefined();
    expect(Array.isArray(result.allowed_output_type)).toBe(true);
    expect(Array.isArray(result.blocked_output_type)).toBe(true);
    expect(["parsed", "rejected", "error"]).toContain(result.parse_status);
    expect(["safe", "flagged", "blocked"]).toContain(result.safety_status);
  });
});

describe("Nexus Research Adapter — Classification and Routing", () => {
  it("credit utilization artifact routes to Scorecard recommendation draft", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "nexus_research/research_inbox/credit_utilization/utilization_scoring.md",
      content: "# Credit Utilization Scoring\n\nUtilization ratio below 30% is recommended for optimal score impact.",
    }));
    expect(result.category).toBe("credit_utilization");
    expect(result.routing_target).toBe("scorecard_recommendation");
  });

  it("business funding artifact routes to Funding Readiness Plan draft", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "nexus_research/research_inbox/business_funding/sba_overview.md",
      content: "# SBA Loan Overview\n\nSBA 7(a) loans provide business funding for qualifying businesses.",
    }));
    expect(result.category).toBe("business_funding");
    expect(result.routing_target).toBe("funding_readiness_plan");
  });

  it("affiliate artifact requires Ray Review", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "nexus_research/research_inbox/affiliates/bank_referral.md",
      content: "# Bank Affiliate Referral\n\nBluevine affiliate program offers commission for referrals.",
    }));
    expect(result.category).toBe("affiliate_offer");
    expect(result.ray_review_required).toBe(true);
    expect(result.admin_only).toBe(true);
  });

  it("client education draft requires approval", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "nexus_research/research_inbox/client_education/credit_basics.md",
      content: "# Credit Report Basics\n\nUnderstanding your credit report is the first step.",
    }));
    expect(result.category).toBe("client_education");
    expect(result.routing_target).toBe("client_education_draft");
    expect(result.ray_review_required).toBe(true);
  });
});

describe("Nexus Research Adapter — Safety Checks", () => {
  it("guarantee language is flagged", () => {
    const flags = detectGuaranteeFlags("This will guarantee approval for funding.");
    expect(flags.length).toBeGreaterThan(0);
    expect(flags.some(f => /guarantee|approval/i.test(f))).toBe(true);
  });

  it("risky artifact becomes admin-only", () => {
    const result = adapter.processCandidate(makeCandidate({
      content: "# Risky Research\n\nThis guarantees approval and instant funding.",
    }));
    expect(result.guarantee_flags.length).toBeGreaterThan(0);
    expect(result.admin_only).toBe(true);
    expect(result.safety_status).toBe("blocked");
  });

  it("compliance flags are detected", () => {
    const flags = detectComplianceFlags("FCRA compliance requires specific dispute procedures.");
    expect(flags).toContain("FCRA");
  });

  it("safe artifact is not admin-only", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "nexus_research/research_inbox/credit_utilization/basics.md",
      content: "# Credit Utilization Basics\n\nUtilization is the ratio of balance to credit limit.",
    }));
    expect(result.guarantee_flags.length).toBe(0);
    expect(result.admin_only).toBe(false);
    expect(result.safety_status).toBe("safe");
  });
});

describe("Nexus Research Adapter — No-Supabase and Isolation Guards", () => {
  it("no Supabase import is added to Alpha", () => {
    const alphaFiles = [
      join(ROOT, "src/hermes/alpha/alphaResearchFileAdapter.ts"),
      join(ROOT, "src/hermes/alpha/alphaScoring.ts"),
    ];
    for (const file of alphaFiles) {
      if (existsSync(file)) {
        const content = require("fs").readFileSync(file, "utf-8").toLowerCase();
        expect(content).not.toContain("from '@supabase");
        expect(content).not.toContain("from \"@supabase");
        expect(content).not.toContain("import.*supabase");
        expect(content).not.toContain("createclient");
      }
    }
  });

  it("Nexus Research adapter does not connect Supabase", () => {
    const adapterFile = join(ROOT, "src/hermes/nexus/nexusResearchAdapter.ts");
    const content = require("fs").readFileSync(adapterFile, "utf-8").toLowerCase();
    expect(content).not.toContain("supabase");
    expect(content).not.toContain("createclient");
    expect(content).not.toContain("from '@supabase");
  });

  it("no Oanda import is added", () => {
    const adapterFile = join(ROOT, "src/hermes/nexus/nexusResearchAdapter.ts");
    const content = require("fs").readFileSync(adapterFile, "utf-8").toLowerCase();
    expect(content).not.toContain("oanda");
    expect(content).not.toContain("oandapy");
  });

  it("no external provider call occurs", () => {
    const adapterFile = join(ROOT, "src/hermes/nexus/nexusResearchAdapter.ts");
    const content = require("fs").readFileSync(adapterFile, "utf-8").toLowerCase();
    expect(content).not.toContain("fetch(");
    expect(content).not.toContain("axios");
    expect(content).not.toContain("http.request");
    expect(content).not.toContain("xmlhttprequest");
  });

  it("no send/publish/charge/trade action exists", () => {
    const adapterFile = join(ROOT, "src/hermes/nexus/nexusResearchAdapter.ts");
    const content = require("fs").readFileSync(adapterFile, "utf-8").toLowerCase();
    expect(content).not.toContain("send_email");
    expect(content).not.toContain("publish_post");
    expect(content).not.toContain("charge_payment");
    expect(content).not.toContain("execute_trade");
    expect(content).not.toContain("place_order");
  });
});

describe("Nexus Research Adapter — Empty Inbox Handling", () => {
  it("empty inbox is valid and honestly reported", () => {
    const readmeFiles: string[] = [];
    const artifactFiles: string[] = [];

    for (const cat of NEXUS_INBOX_CATEGORIES) {
      const catDir = join(NEXUS_RESEARCH_INBOX, cat);
      if (existsSync(catDir)) {
        const files = readdirSync(catDir);
        for (const f of files) {
          if (f === "README.md" || f.startsWith("README_")) readmeFiles.push(f);
          else artifactFiles.push(f);
        }
      }
    }

    expect(readmeFiles.length).toBeGreaterThanOrEqual(NEXUS_INBOX_CATEGORIES.length);
    expect(artifactFiles.length).toBe(0);
  });
});

describe("Nexus Research Adapter — Fixture Labeling", () => {
  it("fixture artifacts are clearly labeled as fixtures", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "nexus_research/research_inbox/credit_utilization/fixture_test.md",
    }));
    expect(result.evidence_quality).toBe("demo");
  });

  it("non-fixture artifacts are marked unverified", () => {
    const result = adapter.processCandidate(makeCandidate({
      path: "nexus_research/research_inbox/credit_utilization/real_research.md",
    }));
    expect(result.evidence_quality).toBe("unverified");
  });
});

describe("Nexus Research Adapter — Draft Outputs", () => {
  it("admin note includes all required fields", () => {
    const result = adapter.processCandidate(makeCandidate());
    const adminNote = adapter.generateAdminNote(result);
    expect(adminNote.summary).toBeDefined();
    expect(adminNote.category).toBeDefined();
    expect(adminNote.evidence_quality).toBeDefined();
    expect(Array.isArray(adminNote.risk_compliance_notes)).toBe(true);
    expect(adminNote.recommended_internal_action).toBeDefined();
    expect(Array.isArray(adminNote.ray_review_items)).toBe(true);
  });

  it("Ray Review draft includes blocked actions", () => {
    const result = adapter.processCandidate(makeCandidate());
    const draft = adapter.generateRayReviewDraft(result);
    expect(draft.title).toBeDefined();
    expect(draft.source_artifact).toBeDefined();
    expect(draft.recommendation).toBeDefined();
    expect(draft.why_it_matters).toBeDefined();
    expect(["yes", "no", "pending"]).toContain(draft.client_facing_allowed);
    expect(draft.approval_required).toBe(true);
    expect(draft.blocked_actions).toContain("no_send");
    expect(draft.blocked_actions).toContain("no_publish");
    expect(draft.blocked_actions).toContain("no_charge");
    expect(draft.blocked_actions).toContain("no_trade");
  });
});

describe("Nexus Research Adapter — Category Routing Table", () => {
  it.each([
    ["credit_repair", "credit_readiness_knowledge"],
    ["credit_utilization", "scorecard_recommendation"],
    ["business_setup", "business_setup_checklist"],
    ["fundability", "fundability_checklist"],
    ["business_funding", "funding_readiness_plan"],
    ["grants", "grant_opportunity_review"],
    ["lender_program", "lender_matching_notes"],
    ["affiliate_offer", "affiliate_offer_approval"],
    ["client_education", "client_education_draft"],
    ["compliance", "compliance_guardrail"],
    ["manual_note", "manual_review_queue"],
  ] as const)("category %s routes to %s", (category, expectedRoute) => {
    expect(routeCategory(category)).toBe(expectedRoute);
  });
});

describe("Nexus Research Adapter — Path Validation", () => {
  it.each([
    ["nexus_research/research_inbox/credit_repair/note.md", true],
    ["nexus_research/research_inbox/credit_utilization/note.md", true],
    ["nexus_research/research_inbox/business_setup/note.md", true],
    ["nexus_research/research_inbox/business_funding/note.md", true],
    ["nexus_research/research_inbox/grants/note.md", true],
    ["nexus_research/research_inbox/lenders/note.md", true],
    ["nexus_research/research_inbox/affiliates/note.md", true],
    ["nexus_research/research_inbox/compliance/note.md", true],
    ["nexus_research/research_inbox/client_education/note.md", true],
    ["nexus_research/research_inbox/manual_notes/note.md", true],
    ["reports/hermes_alpha/note.md", false],
    ["../../.env", false],
    ["nexus_research/research_inbox/../../secret.md", false],
    ["nexus_research/research_inbox/credit_repair/note.json", false],
    ["nexus_research/research_inbox/credit_repair/note.exe", false],
  ])("path %s approved=%s", (path, expectedApproved) => {
    expect(isApprovedInboxPath(path.toLowerCase())).toBe(expectedApproved);
  });
});
