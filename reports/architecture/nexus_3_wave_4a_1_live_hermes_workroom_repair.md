# Nexus OS 3.0 — Wave 4A.1 Live Hermes Workroom Repair

Generated: 2026-07-18

## 1. Starting checkpoint

- Branch: `main`
- Starting HEAD: `be92c8d83f3b300575223cf81091968dc6574f22`
- Starting commit message: `certify nexus hermes conversation and memory architecture`
- Production target: `https://goclearonline.cc/admin#hermes`
- Required room: Hermes CEO Advisor

## 2. Worktree safety

The worktree contained a large unrelated dirty set at start, including Alpha, Telegram, trading, runtime reports, caches, temporary files, and previous local artifacts. Only Hermes Workroom repair files, focused tests, and Wave 4A.1 reports/status files are in scope for this repair.

No destructive git commands were used. No credentials, tokens, customer PII, real credit reports, SmartCredit credentials, live Stripe changes, or external framework installations were added.

## 3. Exact reproduction

Authenticated production reproduction showed the live Workroom returned the bad answer for:

```text
what should we focus on today?
```

Observed bad response:

```text
I can reason from the allowed unknown context, but I need a concrete decision or entity to produce a useful plan.
```

The clean authenticated Playwright reproduction did not re-trigger the visible error boundary for `n is not a function`, including after greeting, priority, and action-producing messages. The failure remained actionable because the source audit found a live-only render/persistence contract split matching the manual symptom: response persistence succeeded, refresh removed the failing live-only shape, and the persisted response rendered.

## 4. Original stack trace

- Production minified error reported by manual test: `n is not a function`
- Clean-session unminified stack: not captured because the crash did not reproduce in the clean authenticated browser run.
- Source-level failure class repaired: unnormalized live Workroom response/action shape reached React rendering; stored messages were persisted as `{ role, text }`, so refresh used a different, stripped render path.

## 5. Root cause

Two separate issues converged in the live Workroom:

1. The Hermes CEO Advisor Workroom was still using `src/lib/hermesBrainPipeline.ts` instead of the canonical Wave 4A engine.
2. Live messages and hydrated messages did not share one normalized serializable response shape. Live messages could carry `uiActions` and callback-dependent render data, while `hermesStore.saveMessages` persisted only `{ role, text }`. Refresh therefore avoided the live action/render path and displayed the already-persisted answer.

The bad fallback string came from `src/lib/hermesBrainPipeline.ts`:

```text
I can reason from the allowed unknown context, but I need a concrete decision or entity to produce a useful plan.
```

## 6. Live response path

Before repair:

```text
NexusAdminUI
  -> HermesWorkroom
  -> SpecialistWorkroom
  -> HermesChatPanel
  -> handleHermesMessage from hermesBrainPipeline
  -> live message shape
  -> HermesMessageBubble
```

After repair:

```text
NexusAdminUI
  -> HermesWorkroom
  -> SpecialistWorkroom
  -> HermesChatPanel
  -> runHermesConversation
  -> normalizeHermesWorkroomResponse
  -> serializable Workroom message
  -> same normalized shape for persistence and render
  -> HermesMessageBubble
```

## 7. Legacy versus canonical router path

- `src/lib/hermes/hermesConversationEngine.ts`: canonical for the Hermes CEO Advisor Workroom.
- `src/components/HermesChatPanel.jsx`: thin adapter into the canonical engine.
- `src/lib/hermesBrainPipeline.ts`: compatibility source only; no longer authoritative for the CEO Advisor Workroom.
- `src/lib/hermesResponseRouter.ts`: adapter for other Hermes entry points.

## 8. Response-contract repair

Added `src/lib/hermes/hermesWorkroomResponse.ts` with one renderable, serializable Workroom contract:

- message ID
- role
- text
- mode
- intent
- response strategy
- evidence state
- confidence
- created timestamp
- typed action descriptors
- memory/context/warning arrays

Every live canonical result is normalized before state insertion, persistence, action rendering, and refresh hydration.

## 9. Action callback and serialization audit

Workroom actions are now persisted as data only:

- action type
- action ID
- label
- enabled state
- approval requirement

Callbacks are rehydrated in `HermesChatPanel` from action type. JavaScript functions, closures, and React event objects are not stored in Supabase/local storage.

## 10. State and persistence audit

`src/lib/hermesChatStore.ts` now preserves the normalized `workroomResponse` payload. Refresh and live render use the same validation and normalization path.

## 11. Operating-context repair

Added `src/lib/hermes/hermesOperatingContext.ts` and connected the visible operating evidence used by `HermesContextPanel` to the canonical engine through `HermesChatPanel`.

The Workroom now receives structured priorities, approvals, revenue actions, blockers, system health, and unknowns. Priority answers use the Nexus P0-P4 order.

## 12. Executive priority routing

Expanded priority classification for paraphrases such as:

- what should we focus on today?
- what should we do first?
- what needs my attention?
- where should we start?
- what is the top priority?
- give me today’s priorities
- what is the biggest problem right now?
- what should Nexus handle first?

The authenticated Workroom answer now recommends the top current operating-context item directly and includes rationale, risk/dependency, and first step.

## 13. Fallback repair

The unknown-context fallback no longer controls the Hermes CEO Advisor Workroom. It remains only in the compatibility pipeline for older paths that have not yet been retired.

## 14. Multi-turn memory result

Authenticated production-equivalent Playwright passed the required sequence:

```text
good morning
what should we focus on today?
why that one?
is that realistic?
what would stop us?
go deeper on number 2
turn that one into a task
reload
```

Results:

- no refresh required for live response
- no render error
- no unknown-context fallback
- follow-ups retained context
- numbered reference resolved
- no task was created before explicit action intent
- persisted messages rendered after reload

## 15. Production build result

`npm run build`: PASS with the existing Vite large chunk warning.

## 16. Authenticated browser result

`E2E_ENABLE_AUTHENTICATED=true npx playwright test tests/e2e/hermes-live-workroom-certification.spec.ts --reporter=line`

Result: PASS 7/7.

Browser gates:

- page errors: 0
- console errors: 0
- response without refresh: PASS
- operating-context answer: PASS
- multi-turn memory: PASS
- explicit action separation: PASS
- responsive desktop/laptop/tablet/mobile: PASS
- client denial from Executive Workroom: PASS

## 17. Security result

- RLS: PASS 45/45
- Alpha Supabase access: still prohibited
- Stripe: test mode preserved
- Live trading: still blocked
- External frameworks: none installed
- Database migrations: none added
- Secrets/PII: no values added to reports or source

## 18. Files changed

- `src/components/HermesChatPanel.jsx`
- `src/components/HermesMessageBubble.jsx`
- `src/lib/hermes/hermesOperatingContext.ts`
- `src/lib/hermes/hermesWorkroomResponse.ts`
- `src/lib/hermes/hermesModeClassifier.ts`
- `src/lib/hermes/hermesResponseStrategy.ts`
- `src/lib/hermesChatStore.ts`
- `src/lib/hermesUiActions.ts`
- `src/lib/executive/hermesExecutiveAdvisor.ts`
- `src/lib/capabilities/capabilityRegistry.ts`
- `tests/hermes_live_workroom_contract.test.ts`
- `tests/e2e/hermes-live-workroom-certification.spec.ts`
- required Wave 4A.1 reports/runtime status files

## 19. Known limitations

The original unminified stack for `n is not a function` could not be captured because the crash did not reproduce in a clean authenticated browser session. The repaired source-level contract addresses the observed symptom class: live render path differed from refresh hydration and allowed unnormalized action/render state into the message component.

Telegram was not the primary target. The admin Workroom now uses the canonical engine; Telegram compatibility remains bounded to shared adapter behavior unless separately certified.

## 20. Readiness for Department Operations

Hermes CEO Advisor Workroom is no longer blocked by the observed live runtime/context defects. Department Operations may proceed only if Ray accepts the remaining limitation that the original minified production stack was not reproduced after clean-session testing.
