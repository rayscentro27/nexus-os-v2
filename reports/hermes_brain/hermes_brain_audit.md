# Hermes Brain Architecture Audit

Date: 2026-07-02
Mode: audit only; repository inspection and safe local checks
Scope: current chat pipeline, routing, rendering, memory, retrieval, provenance, approvals, scheduling, tests, and governance

## Executive summary

Hermes has a real policy pipeline, but it is not yet a layered operating system. The active UI entry points converge on `handleHermesMessage`, which builds one `RouteDecision`, attaches policy-permitted context, executes a route in a large switch, renders text, then records memory and a routing trace. This is materially better than independent UI responders, but route recognition and response semantics remain coupled to ordered regular expressions and ad hoc text handlers.

The dominant root cause is not simply “fallback is first.” Fallback is last. It wins because normal language is absent from narrower earlier matchers. A secondary cause is the generic `process_settings_reports_status -> local_status` renderer, which satisfies policy metadata but not the user's status question. The system also conflates a permission to use a source with actually reading and interpreting that source.

Highest-impact examples:

- `how is the system health` does not match the dedicated `system_health_report` phrase set; it falls to the broad status family and can return only “local system health evidence is allowed.”
- `is the research engine working` routes to `process_settings_reports_status`, whose default handler does not inspect a research report or return configured state, last run, blockers, and next action.
- `do we have any clients` is not covered by the protected client inventory syntax and can reach client local reasoning rather than an authenticated source-backed lookup.
- `what did you get that last response from` is not explicitly covered by the trace classifier's natural-language variants and is vulnerable to generic clarification.
- `prepare specialist handoff` has no first-class route; action handling is largely pronoun/keyword based.
- `schedule an audit` correctly remains draft-only, but it asks for details through route-local regexes rather than a scheduling contract.
- Selection state, advisory continuity, fallback continuity, conversation state, and traces are separate module globals, but advisory/fallback are attached through the broad `longTermMemory` permission flag. This is a policy-boundary mismatch even though the variables are separate.

No behavior, scheduler, database, publication, email, billing, or external service was changed or invoked by this audit.

## Files inspected

Primary runtime:

- `src/components/HermesChatPanel.jsx`, `src/components/HermesInlineDrawer.jsx`, `src/admin/NexusAdminUI.jsx`
- `src/lib/hermesBrainPipeline.ts`, `hermesPriorityRouter.ts`, `hermesRouteDecision.ts`, `hermesDomainClassifier.ts`
- `src/lib/hermesContextPacketBuilder.ts`, `hermesAnswerRenderer.ts`, `hermesRoutingTrace.ts`
- `src/lib/hermesConversationState.ts`, `hermesMemoryStores.ts`, `hermesMemoryEligibility.ts`, `hermesAdvisoryContinuity.ts`, `hermesFallbackContinuity.ts`
- `src/lib/hermesLiveContext.ts`, `hermesReportContextAdapter.ts`, `hermesSupabaseContextAdapter.ts`, `hermesSourceReasoner.ts`
- `src/lib/hermesTraceQuestionHandler.ts`, `hermesSystemHealthStatus.ts`, `hermesCommonConversation.ts`, `hermesOpportunityAdvisor.ts`
- `src/lib/hermesProviders.ts`, `supabase/functions/hermes-chat/index.ts`, `supabase/functions/hermes-search/index.ts`
- `src/data/reportRegistry.js`, `systemHealthData.js`, `researchEngineData.js`, `clientsData.js`, `businessOpportunitiesData.js`, `monetizationData.js`, `rayReviewData.js`, `hermesPageContext.js`

Tests and evidence:

- Hermes-focused tests under `tests/hermes*.test.ts`, plus `tests/ray_review_persistence.test.ts` and `tests/supabase_connection_truth.test.ts`
- Existing `reports/hermes_*` routing, continuity, policy, and regression reports
- Governance docs including approval, scheduler, universal action, data boundary, redaction, research autonomy, and chat persistence policies under `docs/operations/`
- Hermes helper scripts under `scripts/hermes/` and UI smoke/test scripts under `scripts/ui/`

## Current architecture

1. Chat surfaces call `handleHermesMessage` directly. Display history is persisted separately by `hermesChatStore`; brain state is module memory.
2. `normalizeHermesRoutingInput` and `classifyHermesDomain` provide lexical classification.
3. `routeHermesPriority` applies a fixed, early-return precedence chain.
4. `createRouteDecision` derives allowed/blocked context from memory, retrieval, model, diagnostic, and action policies.
5. `buildContextPacket` conditionally attaches page context, trace, selection state, static long-term context, advisory state, and fallback state.
6. `executeRoute` in `hermesBrainPipeline.ts` dispatches all route families and contains many renderers inline.
7. `renderHermesAnswer` mostly passes the handler text through and only suppresses a small diagnostic-leak regex.
8. The pipeline updates conversation/selection/advisory/fallback state and writes a module-local routing trace.
9. Supabase reads occur only for selected explicit retrieval/revenue routes and require configured client plus authenticated session/RLS.
10. The edge model function is downstream of model-permitted routes and has input, provider, privacy, dangerous-action, and token guards.

## Failure signatures

| Signature | Location/component | Trigger | Assessment and accidental prompts |
|---|---|---|---|
| `I can reason from the allowed ... context` / `need a concrete decision` | `hermesBrainPipeline.ts`, `local_reasoning` | Any recognized domain not captured by a specific route/renderer | Dangerous generic renderer. Direct but syntactically uncovered status/record questions can hit it, including client and research variants. |
| `I need one more detail` / `general recommendation, a Nexus build plan...` | `hermesBrainPipeline.ts`, `fallback_clarification` | Final route when no matcher wins | Appropriate only for genuine ambiguity; dangerous for provenance, handoff, ordinary status, and reference phrases omitted by regex coverage. |
| `I do not have enough verified Nexus data` | `hermesBrainPipeline.ts`, client branch of `local_reasoning` | Client domain without protected inventory recognition | Honest wording, wrong execution order for record questions: it should attempt the approved read first and report the exact auth/RLS/table blocker. |
| `eligible target` | `hermesBrainPipeline.ts`, `approval_action_prepare` | Vague action reference or Ray Review request with no resolvable selection | Appropriate safety constraint, but “specialist handoff” lacks a dedicated contract and can receive a misleading target clarification. |
| `allowed context` | `hermesAnswerRenderer.ts`, `hermesTraceQuestionHandler.ts`, route diagnostics | Diagnostic suppression fallback or explicit trace display | Appropriate in an explicitly requested technical trace; dangerous as end-user answer text. Suppression does not catch the generic `local_status` wording. |
| `local_status` | `hermesBrainPipeline.ts` default status handler; routing audit | Broad process/settings/research/system status route without specialized renderer | Dangerous. Reports permission rather than operational state. Prompts such as `is the research engine working` can hit it. |
| `selectionMemory` | memory stores, route/context builder, pipeline/tests/reports | Lists, ranking, recommendation, reference, action target | Appropriate concept; risk comes from module-global lifetime, duplicated state, incomplete expiry enforcement, and hardcoded list rows. |
| `lastAdvisoryContext` | No active symbol found; equivalent is module-global `AdvisoryContinuityState` | Advisory-producing route followed by a recognized follow-up | Naming drift suggests prior patches/docs and runtime are not governed by one schema. |
| `advisory_followup` | priority router, pipeline, tests/reports | Short follow-up plus live advisory state and domain guard | Correct separate route, but matching is narrow, stored summaries are partly templated, and its permission is represented as `long_term_allowed`. |
| `route dominance` | existing audit/report artifacts | Regression evidence | Confirms fallback and generic status dominance; useful evidence but reports can become stale and are not executable contracts. |

Related exact phrase not found: `I can reason from the allowed` appears as a longer template. The phrase `I need a concrete decision` is part of that same template. `clarification` and `fallback` occur broadly across runtime, tests, data loaders, and unrelated UI fallback code; route-relevant occurrences are catalogued above.

## Response-contract gap report

| Required contract | Current state | Gap |
|---|---|---|
| `casual_common` | Dedicated route, no retrieval/model/selection memory | Mostly clear; some answers inject Nexus/work status and “strong progress,” violating a strict no-Nexus casual contract. |
| `nexus_advisory` | Split across `general_advisor`, `opportunity_aware_recommendation`, `nexus_build_planning`, `revenue_reasoning`, `local_reasoning` | No single schema for recommendation, assumptions, evidence, risks, and next safe action. |
| `advisory_followup` | Dedicated short-lived state and renderer | No relevance score/entity binding; broad long-term permission; templated answers may overstate continuity. |
| `system_health` | Dedicated renderer exists for narrow phrases | Contract is incomplete/stale: hardcoded commit/test counts; no freshness object; normal wording misses route. |
| `approvals_pending` | Protected live read of `task_requests` and `approvals` | Strongest operational contract, but a successful query with partial table errors can still claim live data; source freshness is only request timestamp. |
| `research_engine_status` | No dedicated route/renderer | Generic `local_status`; lacks configured/unknown, last run, source, blockers, next action. |
| `client_records` | Explicit list variants can query `client_profiles` | Singular/normal variants miss; generic row summarizer; no record-level contract or exact RLS/auth/table blocker taxonomy. |
| `business_opportunity` | Live query attempt plus hardcoded `OPPORTUNITIES` list | Static list is presented even when unrelated to returned rows; source fusion is not item-level and selection memory stores hardcoded rather than retrieved entities. |
| provenance/source/meta | Dedicated last-trace route | Good foundation; phrase coverage incomplete; trace is module-local, lacks durable source snapshots/freshness and explicit assumptions/confidence in the plain response. |
| `action_or_delegation` | Generic approval action route | No first-class specialist/delegation renderer; outcome limited to local draft/block; target resolution is selection-centric. |
| Ray Review draft | Conversation-only draft with action proof | Safe and explicit, but not a structured draft object and not clearly distinct from an approval record creation workflow. |
| scheduling draft | Draft-only; scheduler start blocked | Contract is embedded regex/text; target/time parsing narrow; no structured schedule draft or timezone confirmation. |
| fallback clarification | Final route plus four-turn fallback continuity | Option list is fixed and not derived from competing route candidates; ordinary uncovered intents are treated as ambiguity. |

## Top root causes

1. **Route precedence issue / keyword overfitting:** ordered regex families are both classifier and precedence law. First-match semantics make lexical accidents architectural decisions. `model` is handled specially in places, but the global model/status family remains broad.
2. **Renderer contract issue:** route IDs do not map to typed response contracts. The generic status and local reasoning handlers can legally return policy prose without answering the question.
3. **Generic fallback dominance / missing routes:** research status, broad client lookup, specialist handoff, and some provenance language have no robust first-class recognition.
4. **Memory boundary issue:** independent stores exist, but permission types do not independently model advisory and fallback memory; module-global state is shared across all callers in the JavaScript process and display persistence is disconnected from brain continuity.
5. **Data source/read failure:** “allowed to retrieve” is not equivalent to “retrieved.” Local report adapters and static data are not consistently invoked by status routes, and Supabase partial failure semantics are too coarse.
6. **Missing regression test:** many patch-specific tests exist, but there is no single table-driven golden contract suite covering route, source, memory, banned phrases, and side-effect proof together.
7. **Safety/governance gap:** runtime gates are strong for obvious verbs, but governance is distributed among regexes, edge firewall, configs, docs, and route text rather than one enforceable action policy.
8. **UI/backend/auth verification blocker:** local inspection cannot prove production bundle version, browser session, RLS behavior, or current Supabase contents.

## Risks and safety notes

- Module-global brain memory can cross chat surfaces and potentially users/tenants in a long-lived shared runtime; there is no session-keyed store in this pipeline.
- Static imported reports can be stale at build time. `reportRegistry` and hardcoded health text do not provide a unified freshness contract.
- A query is considered live if at least one table succeeds. Answers need per-source success/error state to avoid false completeness.
- `hermesChatStore.clearHistory()` clears display persistence but the UI does not call `resetConversationState()`, so visible history and brain memory can diverge.
- `conversationHistory`, `userSession`, and `tenantId` exist in the pipeline input but are not used to isolate module state.
- No scheduler, external write, paid model, email, charge, publish, deployment, or database mutation was run.

## Artifact index

- [Current route map](hermes_brain_route_map.md)
- [Memory and retrieval map](hermes_brain_memory_map.md)
- [Golden prompt suite](hermes_brain_golden_prompts.md)
- [Master refactor plan](hermes_brain_master_refactor_plan.md)

## Remaining blockers and recommended next prompt

Remaining blockers are authenticated browser/Supabase verification, production deployment/version verification, and confirmation of current live report/table schemas. These do not invalidate the static architecture findings.

**Exact recommended next prompt type: master refactor prompt.** It should authorize only Phase 1 contracts and golden tests first, leaving production verification for a subsequent authenticated browser/Supabase verification prompt.
