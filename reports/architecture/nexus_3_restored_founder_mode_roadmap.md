# Nexus 3 Restored Founder Mode Roadmap

Generated: 2026-07-18
Last updated: 2026-07-19 Wave 4A.3 advisory context ownership repair

## Roadmap decision

The repository supports restoring Founder Mode before adding more revenue, subscription, trading, or large AI workforce scope. The correct sequence is:

```text
Wave 0 — Reconciliation and governance
Wave 1 — Executive and Founder Mode core
Parallel Lane R1 — Repo-intelligence recovery
Parallel Lane R2 — Competitive-pattern library
Wave 2 — Capability OS and governed orchestration
Wave 3 — Knowledge and intelligence layer
Wave 4 — Department operations and automation
Wave 5 — Growth, creative, and customer operations
Wave 6 — Venture studio and advanced expansion
```

## Wave 0 — Reconciliation and governance

Status: this audit.

Scope:

- Verify repository identity and prior certifications.
- Classify dirty worktree and protect unrelated work.
- Reconcile Hermes, Alpha, approvals, work requests, health, revenue, knowledge, automation, and trading boundaries.
- Reconstruct repo-intelligence registry.
- Recommend the first implementation wave.

Exit gate:

- Ray approves or rejects the recommended Wave 1.

## Wave 1 — Executive and Founder Mode core

Goal: give Ray one governed operating surface for the company.

Status: implemented in Wave 1 as the canonical Executive Command Center read model and admin surface.

Build:

- Executive Command Center shell. Completed.
- Daily operating brief. Completed as a deterministic read-model package.
- Hermes executive briefing panel. Completed with executive intent routing.
- Ray Review and Approvals summary. Completed as normalized Executive approval items.
- Work/request status summary. Completed over `task_requests`, `approvals`, `agent_jobs`, and `nexus_events`.
- Department status read model. Completed with truthful activation states.
- Client operations summary. Completed as aggregate/admin-authorized signals.
- Revenue/opportunity summary. Completed with test/live/mock/projected/deferred distinction.
- System health summary. Completed as canonical Executive health adapter.
- Repo Intelligence status and review hooks. Completed as read-only registry view.

Reuse:

- `task_requests`, `approvals`, `agent_jobs`, `nexus_events`.
- Admin auth/RLS.
- Existing reports and connector registries as read-only inputs.
- Existing Hermes/Alpha safety guards.

Do not disturb:

- Nexus 3 client portal.
- Stripe test-mode implementation.
- Live Stripe deferral.
- Client/admin route guards.
- Trading blocks.
- Alpha no-Supabase boundary.

Acceptance gates:

- No client PII in executive summaries.
- Alpha stays read-only and cannot access Supabase.
- Hermes cannot approve as Ray.
- High-risk actions create approval records only.
- Existing RLS and authenticated certification remain green.

Wave 1 limitations:

- No new database tables were created; the first implementation uses read-model adapters.
- Existing duplicate legacy registries remain available underneath the normalized Executive view.
- Full Capability OS persistence is deferred to Wave 2.
- Repo Intelligence remains research-only; no external code or tool was installed.

## Parallel Lane R1 — Repo-intelligence recovery

Goal: preserve Nexus ability to study strong open-source systems without unauthorized integration.

Scope:

- Maintain `reports/runtime/nexus_repo_intelligence_registry.json`.
- Track license/security/maintenance evidence.
- Send only recommendation/status items into Ray Review.
- No cloning, vendoring, package installation, or source copying without explicit approval.
- Include GitHub MCP Server as a planned controlled external tool candidate only.

Placement: B — parallel research lane with limited governance hooks in Wave 1.

## Parallel Lane R2 — Competitive-pattern library

Goal: keep architecture/workflow lessons available without turning every competitor feature into a requirement.

Scope:

- Pattern summaries.
- Feature gap map.
- Cost-saving and money-engine opportunities.
- Legal/security unknowns marked plainly.

## Wave 2 — Capability OS and governed orchestration

Status: IMPLEMENTED in commit `43285f300f6bea15d3e21d43ef6ab54db23af71e`.

Built:

- Canonical capability registry.
- Capability health and dependency model.
- Activation modes and approval levels.
- Rollback/test-plan fields.
- Governed execution preflight over approved internal jobs.
- Capability proposal intake from Repo Intelligence.
- GitHub MCP Reader/Writer governance records without installation.
- Hermes capability-awareness.
- Executive Capability OS visibility.

Do not include live external actions until the capability registry and approval gates are proven.

Known follow-up: durable Supabase-backed capability governance overrides remain deferred until a mutable-state requirement is proven.

## Wave 3 — Knowledge and intelligence layer

Status: IMPLEMENTED in Wave 3 pending final commit.

Built:

- Separation of knowledge, memory, evidence, context, policy, skill, capability, tool, and model.
- Approved evidence provenance.
- Evaluation and freshness checks.
- Restricted retrieval rules by data classification.
- Brain Profile Registry for Hermes, Alpha, Client AI, and planned department brain templates.
- Deterministic retrieval, memory, context assembly, handoff, and structured-output policy.
- Knowledge Health and AI Brain panels in the Executive Command Center.
- Capability OS registration for Wave 3 knowledge and brain capabilities.

Known follow-up: durable Supabase-backed knowledge approval history remains deferred until a mutable-state requirement is proven.

## Wave 4A — Hermes conversation and memory architecture

Status: IMPLEMENTED in Wave 4A.

Built:

- Canonical Hermes conversation pipeline.
- Deterministic conversation-mode classifier.
- Bounded advisory and selection memory contracts.
- Reference resolution for pronouns, numbered items, and named recommendations.
- Deterministic/hybrid/fallback response strategy.

## Wave 4A.4 — Hermes general intelligence and governed tool use

Status: LOCAL_FOCUSED_PASS; live production verification pending for the new commit.

Built:

- Governed Hermes Tool Registry mapped to Capability OS.
- Current-time/date tool using Phoenix/Arizona formatting.
- Project/roadmap status tool.
- Sanitized report catalog and lookup tools.
- Customer aggregate tool that distinguishes synthetic/test evidence from unconfirmed real paying customers.
- Previous-answer provenance tool.
- Active readiness-review topic continuation.
- Project discussion/design mode.
- 200+ general conversation corpus and 40+ holdout evaluation.

Department Operations status after Wave 4A.4: NEXT/PARTIAL. Do not approve Department Operations until the new commit is deployed and live Workroom certification passes.
- Conversation trace and response-quality evaluator.
- Durable certification corpus for greetings, advice, follow-ups, references, status honesty, action separation, page-context conflicts, and historical regressions.
- Executive Hermes Conversation Health panel.
- Capability OS registration for Wave 4A Hermes conversation capabilities.

Known follow-up: deeper retirement of non-Workroom legacy routers remains deferred until a separate migration proves equivalent browser behavior.

## Wave 4A.1 — Live Hermes Workroom runtime and context repair

Status: IMPLEMENTED and browser-certified.

Built:

- Connected the authenticated Hermes CEO Advisor Workroom to the canonical Wave 4A conversation engine.
- Added a normalized serializable Workroom response contract.
- Removed callback/function persistence from Workroom action rendering.
- Connected the visible Operating Context evidence to Hermes priority responses.
- Repaired Executive priority routing for "what should we focus on today?" and related paraphrases.
- Added production-equivalent authenticated Playwright certification for immediate response rendering, persistence after refresh, multi-turn memory, selection resolution, action separation, responsive layouts, and client denial.
- Added Capability OS records for Workroom runtime, Workroom response rendering, operating-context adapter, and live conversation certification.

Acceptance evidence:

- `tests/e2e/hermes-live-workroom-certification.spec.ts`: PASS 7/7.
- Page errors: 0.
- Console errors: 0.
- `npm test`: PASS 1466/1466.
- RLS: PASS 45/45.

Known limitation:

- The original minified production stack for `n is not a function` was not captured because the crash did not reproduce in a clean authenticated session. The source-level live render/persistence contract was repaired and certified.

## Wave 4A.2 — Hermes production stack and Executive intent differentiation

Status: IMPLEMENTED and live-production certified.

Built:

- Traced production `n is not a function` to the Workroom scroll effect returning a non-function cleanup value through React effect lifecycle.
- Repaired `src/components/HermesChatPanel.jsx` so `scrollIntoView` is performed as a side effect and never returned as cleanup.
- Added schema-versioned Workroom localStorage migration for legacy messages.
- Sanitized legacy Workroom actions so callbacks/functions cannot be loaded from storage.
- Split Executive intent routing into priority, risk, revenue, rationale, feasibility, blocker, and deep-dive strategies.
- Segmented Hermes operating context into priorities, risks, revenue actions, blockers, opportunities, system health, and unknowns.
- Added production-style Playwright coverage for legacy state, scroll polyfill return values, zero page errors, zero console errors, response differentiation, action separation, and responsive behavior.

Acceptance evidence:

- `npm run typecheck`: PASS.
- `npm run build`: PASS with existing chunk-size warning.
- `npm test -- --reporter=dot`: PASS 1470/1470.
- RLS: PASS 45/45.
- `tests/e2e/hermes-production-intent-certification.spec.ts`: PASS 7/7 local production.
- `tests/e2e/hermes-live-workroom-certification.spec.ts`: PASS 7/7 local production.

Known limitation:

- Live production post-deploy certification passed against `https://goclearonline.cc` with deployed commit `dc8153aa3b20d3cc0cb3e29ec341285e88caa21f`.

## Wave 4A.3 — Hermes advisory context ownership and topic switching

Status: IMPLEMENTED and live-production certified.

Built:

- Split priority, risk, and revenue recommendation responses into distinct structured advisory contexts.
- Added an active advisory context pointer and bounded advisory history to the canonical Hermes session.
- Marked older advisory contexts superseded when a newer recommendation-producing response is created.
- Preserved active advisory context through greetings, acknowledgements, status answers, and security-boundary answers.
- Added explicit older-topic recall for requests such as `going back to the client live-data flag`.
- Added selected-item continuity so `go deeper on number 2` followed by `turn that one into a task` targets number 2.
- Added serializable Workroom advisory metadata for safe refresh reconstruction without function persistence.
- Added sanitized trace evidence for active-before, active-after, resolved advisory, resolution method, topic switch, supersession, and follow-up semantic.
- Added stale-topic leakage tests and production Workroom advisory-context browser certification.

Acceptance evidence:

- `tests/hermes_advisory_context_ownership.test.ts`: PASS.
- Full unit suite: PASS 94 files / 1476 tests.
- TypeScript: PASS.
- Production build: PASS with existing chunk-size warning.
- RLS: PASS 45/45.
- Local production Workroom advisory-context Playwright: PASS 2/2.
- Existing local production Workroom suites: PASS 14/14.

Exit gate:

- Completed: production served commit `9b37b8c6f7115b5997b774bb52afdc676e2ffd4e` on `main` with bundle `/assets/index-D0QaAbwK.js`; live Workroom advisory-context Playwright passed with zero stale-topic leakage, zero page errors, and zero console errors.

## Wave 4 — Department operations and automation

Wave 4A.4R release gate:

- Hermes general-intelligence work is protected for production release.
- Playwright certification uses the established `playwright/test` package and authenticated `/admin#hermes` route.
- Strict RLS warnings are classified with zero confirmed unsafe findings; authenticated RLS remains 45/45.
- Authenticated live Hermes general-intelligence certification passed at `https://goclearonline.cc/admin#hermes` for implementation commit `03aebef09770b6ffb292f66cf7e9957b2ecb8f4e`.
- Department Operations remains a separate approval decision; this certification removes the Hermes general-intelligence blocker but does not itself approve Department Operations.

Build:

- Data-driven departments.
- Department ownership, KPIs, inboxes, and escalation.
- Bounded internal automations.
- Incident and recovery workflows.

## Wave 5 — Growth, creative, and customer operations

Build:

- Customer communication automation after consent/provider approval.
- Marketing/creative pipelines with publish gates.
- Revenue expansion after controlled customer testing.
- Subscription implementation only after one-time paid service delivery is reliable.

## Wave 6 — Venture studio and advanced expansion

Build later:

- Venture Studio.
- Advanced AI workforce.
- Broader external automation.
- Trading expansions only if legal/risk gates are separately approved.

## Next implementation wave decision

Recommended next wave after Wave 4A.1 certification:

```text
Wave 4 — Department Operations and Governed Automation
```

Approval decision required:

Approve or reject Wave 4 — Department Operations and Governed Automation as the next Nexus 3.0 implementation wave. External tools remain uninstalled, Alpha remains isolated from Supabase, live Stripe remains deferred, and live trading remains blocked unless Ray separately approves a bounded future change.
