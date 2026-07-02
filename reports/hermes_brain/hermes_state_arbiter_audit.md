# Hermes State Arbiter Audit

Date: 2026-07-02

## Executive finding

Hermes can support a partial consolidation. A full rebuild is not required. The current worktree already contains the right structural pieces—intent frames, scoped advisor sessions, a conversation arbiter, successful traces, source authority, and voice-ready rendering—but those pieces do not yet form one authoritative decision path.

The main defect is split authority:

1. `buildIntentFrame()` classifies the message.
2. `routeHermesPriority()` independently selects a route.
3. `arbitrateConversationState()` runs afterward and mutates selected `RouteDecision` fields.
4. `executeRoute()` performs another layer of session-specific matching.
5. Business review handlers add early-return behavior after route execution.
6. Response mode is inferred after rendering rather than controlling rendering.

That layout allows stale sessions, trace rules, selection memory, and route regexes to disagree about the active context.

## Current flow inventory

| Concern | Current location | Finding |
|---|---|---|
| Raw normalization | `hermesIntentClassifier.normalizeMessage`, `hermesInputNormalization.normalizeHermesRoutingInput`, `hermesPromptKind.normalizePrompt` | Three normalization entry points can diverge. The intent frame should own canonical normalization. |
| Intent frame | `hermesIntentClassifier.buildIntentFrame` | Good typed foundation. It records intent, domain, target, action, source need, follow-up, safety, confidence, and signals. |
| Route selection | `hermesPriorityRouter.routeHermesPriority` | Still a long ordered early-return router. It accepts the intent frame but remains independently regex-driven. |
| Central state decision | `hermesConversationArbiter.arbitrateConversationState` | Exists in the worktree, but returns a narrow decision and is applied after routing through mutation. It lacks safety-decision, response-mode, target-action, and explicit stale-session output. |
| Active sessions | `hermesAdvisorSession`, checked by arbiter and `active_session_continue` in pipeline | Scoped and expiring. Session eligibility is regex-based. A session wins too broadly for business phrases and has no paused state. |
| Selection memory | `hermesMemoryStores`, `hermesConversationState`, context packet, priority router | Scoped and expiring, but duplicated with session focus and conversation list state. |
| Last answer | `hermesConversationState.lastAnswerSummary` | Stores only 500 characters, without route/source/target/mode. Not sufficient for reliable rerendering. |
| Last recommendation | Conversation state plus selection memory; session has `lastRecommendation` | Stored through multiple lanes and not reliably updated for every recommendation route. The arbiter currently reads only selection memory. |
| Last safety decision | No dedicated store | Missing. Safety route writes only trace/compact trace facts, and `lastSuccessfulTrace` intentionally excludes safety. This directly causes “why did you block that” failure. |
| Last trace | `hermesRoutingTrace`, compact `lastTurnTraceMemory`, session `lastTrace` field | Multiple representations. `lastTrace` field is not the authoritative source. |
| Last successful trace | `hermesAdvisorSession.lastSuccessfulTraceByScope` | Useful scoped source, but excludes safety and stores no answer text, assumptions, blockers, or response mode. |
| Supabase summaries | `hermesLiveContext.buildLiveSupabaseContext`, `hermesOperationalContracts.renderRecordContract`, plus route-local plain renderers | Per-table results exist, but route-local approval/client renderers bypass the clean contract and reduce source precision. `liveData` means at least one success, which must not be used as table-specific success. |
| Response style | `hermesVoiceReadyRenderer` and late regexes in `hermesBrainPipeline` | Mode is chosen after answer generation. Default output remains raw handler text; CEO/audit commands can be routed elsewhere or fall back. |
| Fallback | Final priority route and default branch in `executeRoute` | Correctly last in those layers, but can still be reached when state arbitration fails to resolve a follow-up. |
| Report cursor | No explicit cursor; inferred from `currentFocus` and list index | “Next” computes from focus, but the review opener does not advance or explicitly establish cursor semantics. Repetition is possible. |
| Business `currentFocus` | `NexusSessionContext.currentFocus` | Present and scoped. Several handlers resolve it independently rather than through one action resolver. |
| Ray Review draft | Inline action route, `draftRayReviewForOpportunity`, and session branch in pipeline | Three paths. Active-target resolution and draft response shape are inconsistent. |

## Required audit answers

1. **Is there already a central state decision function?** Yes: `arbitrateConversationState()`, currently uncommitted. It is incomplete and not authoritative.
2. **Are active sessions checked before last answer / last recommendation?** Recommendation checks precede active sessions in the arbiter, but previous-answer, safety-decision, and response-depth contexts are absent. `executeRoute()` still independently interprets session messages.
3. **Can stale sessions override recent answers?** Yes. A session remains active for ten turns and broad business/report patterns can classify unrelated follow-ups as session continuation.
4. **Does Hermes store `lastSafetyDecision`?** No.
5. **Does Hermes store `lastRecommendation` reliably?** Partially. It exists in selection, conversation, and session stores, but update coverage and read authority are inconsistent.
6. **Does Hermes have response modes: CEO, audit, trace?** Partially. Voice/screen rendering and trace routes exist, but mode selection is late, `screen` is not a strict audit contract, and there is no persisted target for rerendering the last answer.
7. **Does Hermes aggregate Supabase reads into one clean result?** The adapter exposes per-table results and overall verification, but route-local plain answers can contradict table-specific outcomes or discard provenance.
8. **Can the current architecture support partial consolidation?** Yes. The typed frame, session store, scoped memory, source results, and trace ledger are sufficient foundations.
9. **Is a full rebuild required?** No. The safest change is to extend the existing arbiter into one resolved-state contract, add dedicated decision memory/action resolution/rendering, and make the pipeline obey it before route execution.

## Root causes mapped to live failures

- Safety explanation: no safety-decision memory or move type.
- Stale report hijack: session-fit regex is broad; last recommendation is incomplete and previous-answer context is absent.
- Report cursor: cursor is inferred, not stored.
- Business blocker/draft: action resolution is distributed and intent classification does not always preserve active focus.
- Yesterday recap: activity recognition exists in the worktree, but arbiter forces a generic today intent during override.
- CEO/audit versions: response mode is not a global pre-route move.
- Client contradiction: route-local renderer uses overall `liveData`, not `client_profiles` result state, and bypasses `renderRecordContract`.

## Consolidation boundary

Keep the current router and handlers for domain compatibility, but insert one authoritative resolved state before route execution. The router may propose a route; the arbiter must decide winning context, response mode, target, and whether a session is eligible. One action resolver should resolve references. One renderer should apply CEO/audit/trace/casual contracts. The existing session/source adapters can remain behind those layers.
