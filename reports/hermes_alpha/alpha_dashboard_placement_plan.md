# Hermes Alpha Dashboard Placement Plan

## Options

- A — another bot in Nexus Hermes: lowest UI cost, but collapses source authority, memory, tools, and safety boundaries. Reject.
- B — separate top-level section in the same Nexus shell: clear identity and lanes while reusing navigation/auth/layout. Recommended for the first UI.
- C — separate service/project with dashboard link: strongest runtime isolation, but premature operational overhead. Keep as a later deployment option.

## Final recommendation

Use Option B for presentation and module boundaries, with Alpha code under `src/hermes/alpha/`. Do not mount the scaffold yet. If external web/model/trading adapters are introduced, move execution behind a separate service boundary (Option C) while retaining the same dashboard link.

Proposed Alpha navigation: Workroom, Online Research, Research Intake, Business Opportunity Desk, Marketing Asset Studio, Affiliate/Offer Lab, Newsletter, Landing Page, Social Content, Trading Research Lab, Oanda Demo Desk (disabled), Reports, Memory, and Ray Review/Nexus Bridge.

Nexus Hermes remains: Nexus workroom, credit/funding readiness, client intake/admin review, Ray Review, system health, and Nexus reports.

Visual requirements: distinct Alpha label/color, “disabled/mock” badge, source mode, provider/cost, external-action lock, and no shared chat/memory. The bridge accepts only explicit Ray-approved artifacts.
