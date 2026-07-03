import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { createRayReviewProposal } from "../src/hermes/alpha/rayReviewProposal";
import { handleHermesMessage } from "../src/lib/hermesBrainPipeline";

const ui = readFileSync(join(process.cwd(), "src/components/HermesAlphaWorkroom.jsx"), "utf8");
const shell = readFileSync(join(process.cwd(), "src/admin/NexusAdminUI.jsx"), "utf8");

describe("Hermes Alpha Workroom separation and bridge", () => {
  it("labels Alpha offline, draft-only, mock-only, and disconnected", () => {
    expect(ui).toMatch(/Offline/);
    expect(ui).toMatch(/Draft Only/);
    expect(ui).toMatch(/No Supabase/);
    expect(ui).toMatch(/Mock Provider Only/);
    expect(ui).toMatch(/No Oanda Connected/);
    expect(ui).toMatch(/No Publishing \/ Sending \/ Charging \/ Trading/);
  });

  it("mounts Alpha separately and preserves Nexus Hermes", () => {
    expect(shell).toMatch(/Hermes Alpha — Separate/);
    expect(shell).toMatch(/alpha: <ErrorBoundary panelName="Hermes Alpha Workroom"/);
    expect(shell).toMatch(/hermes: <ErrorBoundary panelName="Hermes Workroom"/);
    expect(shell).toMatch(/!\['hermes', 'alpha'\]\.includes\(activePage\)/);
  });

  it("offers no production execution control", () => {
    expect(ui).not.toMatch(/onClick=.*(?:publish|send|charge|trade|oanda)/i);
    expect(ui).toMatch(/button type="button" disabled/);
  });

  it("keeps the Ray Review bridge conversation-only", () => {
    const proposal = createRayReviewProposal({ lane: "business_opportunity", objective: "Mock experiment", recommendation: "Test manually", risk: "low" });
    expect(proposal).toMatchObject({ status: "conversation_draft_only", externalActionAuthorized: false, saved: false, submitted: false });
  });

  it("does not alter GoClear manual-ready Nexus Hermes behavior", async () => {
    const response = await handleHermesMessage({ message: "is GoClear ready to launch?" });
    expect(response.route).toBe("readiness_operating_status");
    expect(response.text).toMatch(/manual-ready/i);
  });
});
