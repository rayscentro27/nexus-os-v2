# Hermes Brain Memory Contracts

Implemented: 2026-07-02

## Scope key

Runtime memory uses `${tenantId || "default"}:${sessionId || userSession.id || "default"}`. Existing callers without identifiers retain the default scope. Full and inline chat surfaces pass a persistent browser session ID from `hermesChatStore`.

## Lanes

| Lane | Runtime store | Contract |
|---|---|---|
| Session conversation | `conversationState` scope map | Bounded history/topic/list state isolated by scope |
| Selection | `selectionByScope` | Typed list/recommendation/selected item, active domain, source provenance, timestamps, turn count, eight-turn expiry |
| Advisory | `stateByScope` in advisory continuity | Topic, summary, originating sources, assumptions, risks, confidence, timestamp, turn count, six-turn expiry |
| Provenance | scoped compact trace plus scoped routing trace ledger | Last route/intent/sources/live read/action proof/confidence for meta answers |
| UI context | per-request `currentPageContext` | Metadata only; never treated as verified operational data |
| Operational state | `LiveHermesResponse` and local report adapters | Request timestamp, per-table success/error, verification state, and blocker |
| Fallback continuity | scoped fallback state | Original ambiguity and bounded option continuation only |

## Boundary rules

- Status, provenance, action, casual, and explicit new-topic routes are evaluated before advisory continuity.
- Advisory memory cannot resolve item ordinals or Ray Review targets.
- Selection memory is attached only when an explicit marker matches an available item.
- Empty selection state cannot authorize `that one` or `number 3` resolution.
- Switching tenant/session scope swaps all active conversation, selection, advisory, fallback, and trace lanes.
- `hermesStore.clearHistory()` now calls `resetConversationState()`, which clears the active brain memory lanes as well as visible local history.

## Concurrency limitation

Scope activation is synchronous module state around a request. It prevents sequential cross-session leakage in the browser runtime. A future server-side concurrent deployment should replace active-scope selection with explicit store objects passed through the request context or async-local request storage.
