# Hermes Rebuild Decision

## PARTIAL CONSOLIDATION

The current architecture can be stabilized and is now substantially more coherent. A full rebuild is not justified. Follow-up cleanup is still needed because route/session/trace authority remains distributed around the consolidated middle layer.

## Fragile files

- `src/lib/hermesPriorityRouter.ts`: long ordered early-return router; still duplicates intent and move detection.
- `src/lib/hermesBrainPipeline.ts`: route execution, state persistence, session handlers, early returns, tracing, and response finalization remain concentrated in one file.
- `src/lib/hermesIntentClassifier.ts`, `hermesPromptKind.ts`, `hermesDomainClassifier.ts`: overlapping lexical classification.
- `src/lib/hermesConversationState.ts`, `hermesMemoryStores.ts`, `hermesAdvisorSession.ts`, `hermesDecisionState.ts`: intentionally separate lanes, but lifecycle orchestration is spread across modules.
- `src/lib/hermesRoutingTrace.ts`, `hermesTraceQuestionHandler.ts`, and advisor-session successful traces: multiple trace representations remain.

## Proposed architecture

`normalize -> intent frame -> conversation move -> state arbiter -> action resolver -> route adapter -> source result -> response contract -> response-mode renderer -> scoped state/trace persistence`

The next pass should make `RouteDecision` an output of the arbiter rather than mutating a route proposed by the legacy router.

## Migration plan

1. Freeze current transcript tests.
2. Move route construction into arbiter-owned route adapters one domain at a time.
3. Extract report and business session handlers from the pipeline.
4. Consolidate last-answer/provenance traces into one typed answer ledger.
5. Remove redundant lexical classifiers only after parity tests pass.
6. Keep the old router behind a feature flag until two production verification cycles pass.

## Rollback plan

- Revert the consolidation commit to restore the prior router/session behavior.
- No schema or production-data migration is involved.
- Session and decision state are in-memory/browser scoped; rollback requires no database repair.
- Preserve the focused transcript suite to demonstrate the regression if rollback becomes necessary.

## Risk

Medium. The changes affect conversational precedence but preserve safety gates, source adapters, route IDs, and external-action restrictions. The largest residual risk is pipeline complexity and asynchronous module-scoped state in a future concurrent server runtime.

## Safest next prompt

Run authenticated production transcript verification for the safety, stale-report, report-cursor, business-review, response-mode, client-empty-success, and timeline sequences. Capture answer text and trace metadata without writing production data.
