# Nexus 3 Restored Founder Mode Roadmap

Generated: 2026-07-18
Last updated: 2026-07-18 Wave 1 implementation

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

Status: IMPLEMENTED in Wave 4A pending final commit.

Built:

- Canonical Hermes conversation pipeline.
- Deterministic conversation-mode classifier.
- Bounded advisory and selection memory contracts.
- Reference resolution for pronouns, numbered items, and named recommendations.
- Deterministic/hybrid/fallback response strategy.
- Conversation trace and response-quality evaluator.
- Durable certification corpus for greetings, advice, follow-ups, references, status honesty, action separation, page-context conflicts, and historical regressions.
- Executive Hermes Conversation Health panel.
- Capability OS registration for Wave 4A Hermes conversation capabilities.

Known follow-up: deeper retirement of the rich workroom router remains deferred until a separate migration proves equivalent browser behavior.

## Wave 4 — Department operations and automation

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

Recommended next wave after Wave 3 certification:

```text
Wave 4 — Department Operations and Governed Automation
```

Approval decision required:

Approve or reject Wave 4 — Department Operations and Governed Automation as the next Nexus 3.0 implementation wave. External tools remain uninstalled, Alpha remains isolated from Supabase, live Stripe remains deferred, and live trading remains blocked unless Ray separately approves a bounded future change.
