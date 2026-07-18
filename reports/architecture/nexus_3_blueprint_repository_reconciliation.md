# Nexus 3 Blueprint Repository Reconciliation

Generated: 2026-07-18

## Executive summary

Nexus OS 3.0 is not merely a GoClear portal. The current repository contains a certified client/admin/revenue foundation plus many internal operating-system components, but the Executive and Founder Mode layer is still fragmented across admin UI panels, reports, local runtime JSON, Supabase tables, and Hermes router modules.

The correct next implementation wave is Executive and Founder Mode Core. Repo Intelligence should run as a parallel read-only research lane with limited governance hooks in Wave 1. No external repository integration, live Stripe activation, live trading, social publishing, customer email sending, or autonomous execution is approved by this audit.

## Repository identity

- Repository: `rayscentro27/nexus-os-v2`
- Working tree: `/Users/raymonddavis/nexus-os-v2`
- Branch: `main`
- Current HEAD: `4f1bd7ea08e4c1b9a33723a236c2f8d189064c7d`
- Remote: `origin https://github.com/rayscentro27/nexus-os-v2.git`
- Dirty entries at audit start: 142
- Remote alignment: branch was up to date with `origin/main`

## Worktree state

Dirty paths were not modified unless they were required audit outputs.

Classification summary:

| Class | Evidence |
|---|---|
| Runtime/cache | `data/cache/youtube/**`, `data/runtime/**`, `reports/runtime/**`, `test-results/**`, `tmp/**` |
| Telegram | `data/runtime/telegram_*`, `reports/telegram/**`, `scripts/ops/nexus_telegram_*` |
| Alpha | `data/alpha/**`, `reports/alpha/**`, `reports/hermes_alpha/**` |
| Prior reports | `reports/first-paid-customer/**`, `reports/stripe-review-certification/**`, `reports/wave-1a-revenue-certification/**` |
| Work orders | `reports/work_orders/**`, `data/runtime/work_order_draft_latest.json` |
| Research/recommendations | `data/recommendations/**`, `reports/advisor_idea_briefs/**`, `reports/hermes/web_search/**` |
| Unknown/unrelated | shell helpers and temp SQL/MJS files in repo root and `tmp/**` |
| Wave audit candidate | files under `reports/architecture/`, `reports/research/`, and `reports/runtime/nexus_repo_intelligence_registry.json` created or updated by this audit |

## Prior certified foundation

| Claim | Current status | Evidence |
|---|---|---|
| Persona A authenticated client workflow | CERTIFIED_AND_UNCHANGED | Playwright authenticated suite passed 18/18 with E2E env loaded. |
| Persona B authenticated client workflow | CERTIFIED_AND_UNCHANGED | Same suite certified ambiguity-safe routing. |
| Persona C authenticated client workflow | CERTIFIED_AND_UNCHANGED | Same suite certified ownership-discrepancy route. |
| Synthetic admin authentication | CERTIFIED_AND_UNCHANGED | Same suite certified admin login and admin route access. |
| Client/admin separation | CERTIFIED_AND_UNCHANGED | App route guards plus browser denial checks passed. |
| Credit/Business legacy stacking repair | CERTIFIED_AND_UNCHANGED | `tests/nexus3_route_replacement.test.ts` passed; Playwright Nexus 3 spec passed. |
| TypeScript and production build | CERTIFIED_AND_UNCHANGED | `npm run typecheck` and `npm run build` passed. |
| RLS 45/45 | CERTIFIED_AND_UNCHANGED | `scripts/checks/certify_authenticated_rls.py` passed 45 checks. |
| Stripe test-mode foundation | CERTIFIED_AND_UNCHANGED | `tests/revenue_activation.test.ts` passed; live mode remains deferred. |
| Uploads and bounded document processing | CERTIFIED_BUT_NEEDS_RECHECK | RLS/storage tables and client UI exist; full document processor was not rerun in this audit. |
| Canonical credit grouping/discrepancies/strategy matching | CERTIFIED_AND_UNCHANGED | RLS checks and targeted readiness/Hermes tests pass; migrations and client adapters remain present. |

## Current verification results

- `npm run typecheck`: PASS
- `npm run build`: PASS, with existing large Vite chunk warning.
- `npx vitest run tests/nexus3_route_replacement.test.ts tests/nexus_connector_registry.test.ts tests/hermes_alpha_no_supabase_guard.test.ts tests/alpha_cost_controller.test.ts tests/alpha_url_review_safety.test.ts tests/alpha_web_search_connector.test.ts tests/hermes_dual_brain_communication.test.ts tests/revenue_activation.test.ts --testTimeout=20000`: PASS, 41/41.
- `npx vitest run tests/hermes_context_layer.test.js tests/hermes_live_context.test.ts tests/hermes_readiness_operating.test.ts tests/hermes_operations_reports.test.ts tests/nexus_operational_reports.test.ts tests/ray_review_persistence.test.ts --testTimeout=20000`: PASS, 72/72.
- `python3 scripts/checks/certify_authenticated_rls.py`: PASS, 45/45.
- `npx playwright test tests/e2e/authenticated-certification.spec.ts tests/e2e/nexus3-final-authenticated-certification.spec.ts --reporter=line`: PASS, 18/18 with ignored E2E env loaded.
- Changed-file secret scan: PASS, no matches for Stripe/Supabase/E2E password patterns.

## Architecture-domain findings

| Domain | Status | Evidence | Recommendation |
|---|---|---|---|
| Executive and Founder Mode | PARTIAL | `NexusAdminUI.jsx`, command center, Ray Review, system health, reports, operations panels. | Build one Executive Command Center authority layer; reuse existing panels as inputs. |
| Hermes | PARTIAL/DUPLICATED | `hermesResponseRouter`, `hermesWorkRouter`, `hermesToolRouter`, `hermesDualBrainRouter`, client Clyde/Hermes engines. | Make `hermesResponseRouter` plus governed adapters the authoritative Ray-facing response layer; preserve client-safe Hermes separately. |
| Alpha | PARTIAL/SAFE_BOUNDARY_PRESENT | `src/hermes/alpha/*`, `noSupabaseGuard`, provider/cost tests. | Keep Alpha separate, read-only, no Supabase access, no live provider activation without approval. |
| Approvals and Ray Review | IMPLEMENTED/PARTIAL | `approvals`, `task_requests`, `RayReviewCenter`, `nexusRequests`, `ledger`. | Use `task_requests` as universal request intake and `approvals` as decision/approval authority. |
| Work Orders and Delegation | DISCONNECTED/DUPLICATED | Work-order reports describe `work_orders`; deployed schema uses `task_requests` and `agent_jobs`. | Do not add `work_orders` yet; canonicalize as `task_requests` -> approved `agent_jobs` with proof events. |
| Departments and Workforce | PARTIAL | `nexusTabs`, `nexusAIDepartmentRoles`, `agent_registry`, dispatcher reports. | Establish department registry after Founder Mode status model is chosen. |
| System Health and Operations | PARTIAL/DUPLICATED | `system_health`, runtime reports, `SystemHealthPanel`, connector registries. | Canonical health should aggregate Supabase health rows plus latest approved runtime reports. |
| Revenue and Opportunity | IMPLEMENTED/PARTIAL | Stripe test checkout/webhook, `client_orders`, `service_fulfillments`, revenue reports. | Keep test mode; live revenue remains owner-deferred. |
| Knowledge and Intelligence | PARTIAL/DUPLICATED | `approved_knowledge`, report registry, memory configs, research reports. | Separate knowledge, memory, evidence, policy, tool, capability, and model registries. |
| Automation and Process Control | PARTIAL/UNSAFE_TO_BROADLY_ACTIVATE | schedulers, feeders, local reports, automation policies, high-risk guards. | Keep manual/dry-run/approval-gated; no daemons started. |
| Trading | UNSAFE_TO_ACTIVATE | Trading scripts, backtest reports, demo connector reports. | Research/backtest only; live trading remains blocked. |
| GoClear and Client Operations | IMPLEMENTED/PARTIAL | Nexus 3 client portal, admin workflow, Supabase/RLS, Stripe test. | Treat as customer operating input to Founder Mode, not as the whole OS. |

## Completed capabilities

- Nexus 3 authenticated client portal with single Credit/Business workspaces.
- Synthetic Persona A/B/C certification.
- Synthetic admin authentication and operational access.
- Client/admin route separation.
- Supabase Auth, tenant membership, client profile, RLS and private document foundations.
- Stripe test-mode checkout/webhook/order/fulfillment foundation.
- Credit parser/canonical account/discrepancy/strategy-match foundations.
- Ray Review UI and approval receipt model.
- Alpha no-Supabase guard and cost controls.
- Connector inventory surfaces.

## Partial capabilities

- Executive Command Center: visible, but not the canonical Founder Mode OS yet.
- Hermes: strong local/router foundation, but several response/advisory layers overlap.
- Ray Review: usable, but split between static data, `task_requests`, `approvals`, localStorage receipts, runtime reports.
- Work delegation: `task_requests` and `agent_jobs` exist; report-only `work_orders` model is not canonicalized.
- Departments: configured in TS and reports, not fully data-driven.
- System Health: UI and reports exist, but no single authoritative score/status source.
- Repo Intelligence: recovered reports exist; runtime registry had to be reconstructed.
- Admin operations: usable and certified, but still visually/semantically carries Nexus v2 surfaces.

## Disconnected capabilities

- Report-heavy automation lanes often generate JSON/Markdown without durable Supabase linkage.
- Open-source repo scouting is not connected to a canonical registry table or Ray Review decision state.
- Several connector registries disagree on connector status and naming.
- Work-order reports describe a `work_orders` table that is not present in current migrations.
- Some research and money-engine outputs live in runtime/manual_publish folders instead of canonical records.

## Duplicate capabilities

- Hermes routing: response router, work router, tool router, priority router, dual-brain router, client Clyde engines.
- Approvals: `approvals`, `task_requests`, Ray Review runtime JSON, localStorage receipts.
- Connector registries: `src/hermes/nexus/nexusConnectorRegistry.ts`, `configs/connector_registry.json`, `reports/operations/nexus_connector_registry_latest.json`, `reports/runtime/connector_registry_latest.json`.
- Health registries: Supabase `system_health`, static `systemHealthData`, runtime health reports.
- Work delegation: `task_requests`, `agent_jobs`, report-only `work_orders`, draft work-order files.

## Obsolete capabilities

- Report-only `work_orders` schema should be superseded by canonical request/job/approval records unless Ray explicitly chooses a new table.
- Legacy client route wrappers are superseded by Nexus 3 workspaces.
- Static Ray Review fallback should remain demo-only once live `task_requests` coverage is complete.

## Missing capabilities

- Canonical Founder Mode dashboard data contract.
- Canonical capability registry with security, approval, dependency, cost, and activation fields.
- Unified Executive System Health source.
- Durable repo-intelligence registry and Ray Review hook.
- Clear department ownership registry and status lifecycle.
- Formal daily executive brief builder tied to live evidence.
- Explicit Alpha-to-Hermes governed handoff record.

## Unsafe or blocked capabilities

- Live Stripe configuration and live card processing: owner-deferred.
- Live trading/funded trading: blocked.
- Social publishing, email/SMS sending, bureau/creditor contact, external customer communications: approval-gated or blocked.
- Alpha unrestricted Supabase access: prohibited.
- External research/crawling with customer PII: prohibited.
- Agent/autonomous execution beyond bounded internal reports: not approved.

## Security findings

- RLS certification passed 45/45.
- Admin access uses `admin_users` and tenant membership checks.
- Alpha no-Supabase guard is implemented and tested.
- Stripe mode isolation tests pass; live mode remains fail-closed/deferred.
- Main residual security risk is governance fragmentation: several UI/report paths can imply capabilities that are not operationally connected.

## Database and RLS findings

Core production-critical objects include `admin_users`, `tenant_memberships`, `client_profiles`, `client_documents`, `client_orders`, `payment_events`, `service_fulfillments`, `task_requests`, `approvals`, `agent_jobs`, `agent_registry`, `nexus_events`, `system_health`, credit parser/canonical/discrepancy/strategy tables, and review-intake tables.

No evidence was found that a production `work_orders` table exists in migrations. Work-order behavior should be modeled through `task_requests`, `approvals`, and `agent_jobs` until a future additive migration is explicitly approved.

## Route findings

- Public: `/`, `/goclear`, `/pricing`, service offer and checkout status routes.
- Client: `/client/*`, guarded through `ClientPortalGate` and `ClientPortalRoot`.
- Preview: `/client/preview`.
- Admin: `/admin/*`, guarded through `AdminGuard` and `AuthGate`.
- Tester: `/invite`, `/tester/*`.
- Legacy risk: internal admin panels still carry v2 naming and older visual style, but are route-guarded.

## Hermes findings

Authoritative Ray-facing layer should be `hermesResponseRouter` backed by safe context adapters, with `hermesDualBrainRouter` used only to route between Nexus operations and Alpha opportunity research. Client-facing Clyde/Hermes engines must stay restricted to client-safe page/readiness/document/review context.

Hermes currently includes canned/static topic knowledge, report-backed context, Supabase-safe status summaries, and deterministic routing. A live model path exists in reports/code but is not fully activated.

## Alpha findings

Alpha remains separate from Nexus Hermes in code and tests. `noSupabaseGuard` and Phase 1 provider behavior show mock/local mode with no unrestricted Supabase access. Web search and URL review are represented as adapters with cost/safety controls, but live provider status varies by environment and is not approved for broad activation.

## Approval and work-order findings

Canonical recommendation:

1. `task_requests`: universal request intake and work proposal record.
2. `approvals`: Ray decision authority for risky/high-impact requests.
3. `agent_jobs`: bounded execution queue only after approval/allowed policy.
4. `nexus_events`: proof/audit log.

Do not create a competing `work_orders` table in Wave 1 unless Ray explicitly approves replacing the above model.

## Department and workforce findings

Departments exist in config/report form, and agents exist in `agent_registry` with explicit permission columns. They are not yet a cohesive Founder Mode workforce system. Department activation must remain governed by risk and approval level.

## Automation findings

Automation is mostly manual CLI, runtime reports, and dry-run feeders. Several scheduled/loop scripts exist, but this audit did not start daemons. The first wave should display automation status and approvals, not grant broader execution.

## Revenue findings

The $97 readiness review test-mode architecture is certified. Production/live payment configuration is intentionally deferred. Revenue dashboards and opportunity reports exist, but subscription/live revenue expansion should not precede Founder Mode governance and controlled customer testing.

## Knowledge findings

Knowledge, memory, evidence, context, policy, capability, tool, and model concepts are mixed across reports/configs. Wave 1 should not build the full knowledge layer, but it should define registry boundaries and display evidence provenance.

## Trading findings

Trading artifacts support research, backtests, demo/practice checks, and Ray Review cards. Live trading is not approved. Preserve `LIVE_TRADING_ENABLED=false`, `LIVE_CAPITAL=false`, and `AUTONOMOUS_STRATEGY_CHANGES=false`.

## GoClear boundary findings

GoClear is a customer/revenue operating domain inside Nexus, not the whole architecture. Founder Mode should summarize client health, revenue status, review backlog, and readiness delivery status without exposing raw customer PII to Alpha or unrestricted assistant layers.

## Recommended canonical systems

| Concern | Canonical system |
|---|---|
| Executive dashboard | New Founder Mode Core view backed by safe aggregate adapters |
| Hermes advisor | `hermesResponseRouter` + safe context adapters |
| Alpha | `src/hermes/alpha/*` with no-Supabase guard and Ray Review handoff |
| Work intake | `task_requests` |
| Approval authority | `approvals` |
| Execution queue | `agent_jobs` |
| Audit/proof | `nexus_events` |
| Client revenue entitlement | `client_orders` + `service_fulfillments` |
| Capability inventory | new read-only canonical registry derived from existing configs/reports in Wave 1 |
| System health | Supabase `system_health` plus runtime report ingest summary |

## First implementation-wave recommendation

Build Executive and Founder Mode Core.

Wave 1 should include:

- Executive Command Center summary.
- Hermes executive briefing.
- Ray Review and Approvals consolidation.
- Governed work/request status from `task_requests`, `approvals`, `agent_jobs`, and `nexus_events`.
- Department status read model.
- Client operations summary.
- Revenue/opportunity summary.
- System-health summary.
- Repo-intelligence status and Ray Review hooks.
- Daily operating brief from existing evidence.

Wave 1 should reuse:

- Existing admin auth/RLS.
- Existing NexusAdminUI panels where useful.
- `nexusTabs`, connector registries, runtime reports, and Supabase tables as inputs.
- Existing Hermes/Alpha safety guards.

Likely additive database changes:

- A small `capability_registry` or `executive_capabilities` table may be needed after design review.
- A `repo_intelligence_candidates` table may be useful later; for Wave 1 use read-only JSON/report ingest unless Ray approves persistence.

Acceptance gates:

- No client PII in Executive summaries.
- Alpha cannot read Supabase.
- Hermes can advise but not approve as Ray.
- High-risk actions create approval records only.
- Work requests and approvals are not duplicated.
- Live Stripe and live trading remain disabled.
- RLS and client/admin separation still pass.

## Explicit non-goals

- No GoClear redesign.
- No live Stripe.
- No subscriptions.
- No live trading.
- No external publishing/email/SMS.
- No broad autonomous workforce.
- No external repo integration.
- No Company Facts Package, Evidence Engine, Venture Studio, or advanced AI workforce implementation.

## Exact approval decision for Ray

Approve or reject the Executive and Founder Mode Core as the first Nexus 3.0 implementation wave, with Repo Intelligence operating as a parallel, read-only, approval-gated research lane and only its status, evidence, and Ray Review hooks included in Wave 1.
