# Nexus — Tab Action Rules (universal)

Every tab follows these (enforced by `nexusActionPolicy` + `nexusRequests` + `ActionStatusBadge`):

1. Reads use `nexusData` (or `listTable`); no per-tab bespoke data access.
2. Every action is classified by `nexusActionPolicy` and labelled with `ActionStatusBadge`.
3. Safe work → owning-tab queue (e.g. Source Intake Capture Queue). It must NOT appear in Approvals.
4. Review-required work → `nexusRequests` files a `task_requests` row AND a linked `approvals` row;
   it appears in Approvals.
5. No button publishes/sends/trades/deploys without an approval (gate unchanged).
6. No raw Mac/v1 command execution from the UI (status only).
7. Hermes may recommend/explain/draft/file task_requests/auto-route safe work — never auto-approve
   risky actions.
8. Disabled/not-connected actions say "Disabled — not connected yet" (no fake actions).
9. Connected actions write a `nexus_events` proof where appropriate.

## Per-tab label guidance (Part 9)
- Approvals: Live. Agent Jobs: Live (queue dry-run only). Creative Studio: Live (publish disabled →
  gated). Opportunity Lab: candidate only. GoClear/Apex: offer changes = needs review. Trading Lab:
  Demo only / live trading hidden-disabled. SEO: Seed. Integrations: status-only (no keys). Ops:
  Live + legacy v1 detected. Events: Live (read). Model Router: Live.
