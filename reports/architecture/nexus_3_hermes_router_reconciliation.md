# Nexus OS 3.0 — Hermes Router Reconciliation

Generated: 2026-07-18
Last updated: 2026-07-19 Wave 4A.2 production stack and intent repair

## Summary

Wave 4A established `src/lib/hermes/hermesConversationEngine.ts` as the canonical conversation contract for Hermes conversational intelligence. Wave 4A.1 connected the authenticated Hermes CEO Advisor Workroom to that canonical engine and normalized Workroom responses before render and persistence.

The live Workroom must not call `src/lib/hermesBrainPipeline.ts` as its authoritative response path.

## Router map

| Router or layer | File | Authority after Wave 4A | Notes |
|---|---|---|---|
| Canonical conversation engine | `src/lib/hermes/hermesConversationEngine.ts` | CANONICAL for conversation mode, memory, response strategy, trace, and quality | New Wave 4A authority |
| Mode classifier | `src/lib/hermes/hermesModeClassifier.ts` | CANONICAL for top-level conversation mode | Runs before narrow intent |
| Memory resolver | `src/lib/hermes/hermesMemoryResolver.ts` | CANONICAL for Wave 4A advisory/session memory | No durable raw chat archive |
| Reference resolver | `src/lib/hermes/hermesReferenceResolver.ts` | CANONICAL for numbered/pronoun advisory references | Uses bounded advisory context |
| Response strategy | `src/lib/hermes/hermesResponseStrategy.ts` | CANONICAL for deterministic/hybrid/fallback selection | No external provider activation |
| Workroom adapter | `src/components/HermesChatPanel.jsx` | THIN_ADAPTER | Routes Hermes CEO Advisor messages into `runHermesConversation`, passes operating context, normalizes responses before persistence/render |
| Workroom response contract | `src/lib/hermes/hermesWorkroomResponse.ts` | CANONICAL for Workroom render shape | Serializable only; no callbacks/functions persisted |
| Workroom action renderer | `src/components/HermesMessageBubble.jsx` | THIN_ADAPTER | Rehydrates action behavior from typed action descriptors |
| Operating context adapter | `src/lib/hermes/hermesOperatingContext.ts` | CANONICAL for Workroom operating-context priority evidence | Consumes the same operating context source as the visible panel |
| Response router | `src/lib/hermesResponseRouter.ts` | ADAPTER | Uses canonical engine for social, advice, status, reference, task, approval, and command modes |
| Brain pipeline | `src/lib/hermesBrainPipeline.ts` | COMPATIBILITY_SOURCE | No longer authoritative for Hermes CEO Advisor Workroom; retains legacy/domain behavior for unmigrated surfaces |
| Priority router | `src/lib/hermesPriorityRouter.ts` | COMPATIBILITY_SOURCE | Retains action/safety/domain policy routing |
| Executive advisor | `src/lib/executive/hermesExecutiveAdvisor.ts` | CANONICAL evidence source for Executive intents | Used by canonical strategy |
| Legacy local conversation helper | `src/lib/hermesConversationBrain.ts` | DEPRECATED_PENDING_RETIREMENT | Not the CEO Advisor Workroom authority |
| Legacy advisory continuity | `src/lib/hermesAdvisoryContinuity.ts` | COMPATIBILITY_SOURCE | Workroom path remains dependent |

## Conflict resolution

Wave 4A resolves the main conflict by classifying conversation mode before narrower page/domain/action routing. Page context is only used when relevant and does not dominate greetings or casual turns.

Wave 4A.1 resolves the production Workroom conflict by making the CEO Advisor room use the canonical engine and one normalized response shape for both live render and refresh hydration. The bad compatibility fallback from `hermesBrainPipeline.ts` no longer handles "what should we focus on today?" in the Workroom.

Wave 4A.2 resolves the remaining production stack failure and intent collapse:

- The minified `n is not a function` stack mapped to React effect cleanup invocation of the value returned by `end.current?.scrollIntoView(...)` in `src/components/HermesChatPanel.jsx`.
- The Workroom scroll effect now uses a block body and returns `undefined`, so a browser/polyfill return value cannot become a React cleanup callback.
- Legacy localStorage messages now migrate to schema version 2 and are normalized before render.
- Executive Workroom questions now route to distinct strategy IDs for priority, risk, revenue, rationale, feasibility, blockers, and deep dives.

## Retirement plan

Do not delete legacy routers until:

1. Workroom consumers are mapped.
2. Browser coverage confirms equivalent behavior.
3. Conversation trace shows no critical traffic remains on superseded local fallbacks.
4. Ray approves a router-retirement wave.

## Wave 4A.1 live Workroom certification

- Route: `/admin#hermes`
- Room: Hermes CEO Advisor
- Browser suite: `tests/e2e/hermes-live-workroom-certification.spec.ts`
- Result: PASS 7/7
- Page errors: 0
- Console errors: 0
- Response without refresh: PASS
- Operating-context answer: PASS
- Multi-turn continuity: PASS
- Action separation: PASS

## Wave 4A.2 production stack certification

- Route: `/admin#hermes`
- Room: Hermes CEO Advisor
- Root cause: effect cleanup contract in `src/components/HermesChatPanel.jsx`
- Original minified symbol: `n`
- Original source symbol: return value of `end.current?.scrollIntoView({ behavior: 'smooth' })`
- Browser suite: `tests/e2e/hermes-production-intent-certification.spec.ts`
- Local production result: PASS 7/7
- Compatibility suite: `tests/e2e/hermes-live-workroom-certification.spec.ts` PASS 7/7
- Page errors: 0 in local production certification
- Console errors: 0 in local production certification
- Legacy persisted-state rendering: PASS
- Priority/risk/revenue differentiation: PASS
- Rationale/feasibility/blocker differentiation: PASS
- Live production post-deploy result: PASS 14/14 against https://goclearonline.cc
