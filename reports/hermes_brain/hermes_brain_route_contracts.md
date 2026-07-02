# Hermes Brain Route Contracts

Implemented: 2026-07-02

## Precedence law

The active `hermesBrainPipeline` now uses `detectPromptKind()` before broad domain routing. The enforced order is:

1. Safety and prohibited execution.
2. Provenance/source/meta.
3. Direct system health, approval, research engine, and client record questions.
4. Specialist handoff, Ray Review, scheduling, and other explicit actions.
5. Explicit page/activity/new-domain routes.
6. Casual/common conversation.
7. Unexpired advisory follow-up.
8. Explicit selection references.
9. Advisory/planning/domain reasoning.
10. One-question fallback clarification.

The implementation retains compatible route IDs where existing integrations depend on them. For example, approvals still use `explicit_domain_retrieval`, but the renderer is now `approvals_pending_contract`. Contract identity is therefore recorded by `answerBuilder`, not inferred only from the legacy route ID.

## Detection helpers

`hermesPromptKind.ts` defines normalization and explicit detectors for provenance, system health, approval status, research status, client inventory, casual human experience, selection references, actions, and new topics. Regex remains a lexical tool; a single generic keyword is not the route contract.

Product phrases such as Tesla Model 3, business model, and pricing model are protected from AI-model usage routing unless AI/provider/cost language is explicit.

## Renderer contracts

| Contract | Required output |
|---|---|
| Casual | Natural answer; no Supabase/model/operational memory |
| Nexus advisory | Recommendation, source limits/assumptions, confidence, next safe action |
| Advisory follow-up | Prior advisory source, confidence, risks/first step, validation action |
| System health | Status, source, evidence, blockers, freshness limits, next action |
| Approvals | Tables checked, verification state, result/count where available, blocker, freshness, next action |
| Research engine | Configuration state, reports checked, last known run, blockers, freshness, next action |
| Client records | `client_profiles` attempt, verification/result, exact blocker, freshness, next action |
| Opportunities | Per-item static provenance; live inventory is reported separately and never attributed to static items |
| Provenance | Intent/route, sources, live-read state, assumptions, confidence, certainty improvement |
| Specialist handoff | Lane, included context, missing fields, local draft state |
| Ray Review | Eligible target or exact missing target; local-only/not-saved action proof |
| Scheduling | Draft-only; missing target/time; no scheduler activation |
| Fallback | One targeted question; no verified-data implication |

## Governance

All model, source, memory, diagnostic, and action permissions continue through `RouteDecision`. External sends, publishing, charges, deployment, destructive writes, scheduler activation, and live/funded trading remain blocked or explicitly approval-gated.
