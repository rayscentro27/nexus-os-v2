# Nexus OS 3.0 — Hermes Router Reconciliation

Generated: 2026-07-18

## Summary

Wave 4A established `src/lib/hermes/hermesConversationEngine.ts` as the canonical conversation contract for Hermes conversational intelligence. Existing routers remain for certified domain workflows and are treated as adapters or compatibility paths.

## Router map

| Router or layer | File | Authority after Wave 4A | Notes |
|---|---|---|---|
| Canonical conversation engine | `src/lib/hermes/hermesConversationEngine.ts` | CANONICAL for conversation mode, memory, response strategy, trace, and quality | New Wave 4A authority |
| Mode classifier | `src/lib/hermes/hermesModeClassifier.ts` | CANONICAL for top-level conversation mode | Runs before narrow intent |
| Memory resolver | `src/lib/hermes/hermesMemoryResolver.ts` | CANONICAL for Wave 4A advisory/session memory | No durable raw chat archive |
| Reference resolver | `src/lib/hermes/hermesReferenceResolver.ts` | CANONICAL for numbered/pronoun advisory references | Uses bounded advisory context |
| Response strategy | `src/lib/hermes/hermesResponseStrategy.ts` | CANONICAL for deterministic/hybrid/fallback selection | No external provider activation |
| Response router | `src/lib/hermesResponseRouter.ts` | ADAPTER | Uses canonical engine for social, advice, status, reference, task, approval, and command modes |
| Brain pipeline | `src/lib/hermesBrainPipeline.ts` | COMPATIBILITY_SOURCE | Retains workroom behavior and existing certified route tests |
| Priority router | `src/lib/hermesPriorityRouter.ts` | COMPATIBILITY_SOURCE | Retains action/safety/domain policy routing |
| Executive advisor | `src/lib/executive/hermesExecutiveAdvisor.ts` | CANONICAL evidence source for Executive intents | Used by canonical strategy |
| Legacy local conversation helper | `src/lib/hermesConversationBrain.ts` | DEPRECATED_PENDING_RETIREMENT | Wording reduced; still used by workroom path |
| Legacy advisory continuity | `src/lib/hermesAdvisoryContinuity.ts` | COMPATIBILITY_SOURCE | Workroom path remains dependent |

## Conflict resolution

Wave 4A resolves the main conflict by classifying conversation mode before narrower page/domain/action routing. Page context is only used when relevant and does not dominate greetings or casual turns.

## Retirement plan

Do not delete legacy routers until:

1. Workroom consumers are mapped.
2. Browser coverage confirms equivalent behavior.
3. Conversation trace shows no critical traffic remains on superseded local fallbacks.
4. Ray approves a router-retirement wave.
