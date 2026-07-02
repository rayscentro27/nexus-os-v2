# Hermes Brain Target Architecture and Master Refactor Plan

This is a proposal only. It does not authorize implementation or deployment.

## Target pipeline

`normalize -> detect safety/action -> classify intent candidates -> resolve references -> apply precedence law -> build typed source plan -> retrieve -> render typed contract -> validate contract/safety -> record scoped memory + trace`

Classification should produce candidates and evidence, not final text. Retrieval should return typed source results. Renderers should accept only the contract-specific inputs they need.

## Route precedence law

1. Hard safety denial for prohibited execution.
2. Explicit action/delegation/Ray Review/scheduling request, always draft or approval-gated.
3. Provenance/meta question about the previous answer.
4. Explicit operational record/status request: approvals, client records, research status, system health, business inventory.
5. Explicit selection reference (`number 3`, `that one`) with eligible scoped selection memory.
6. Relevant advisory follow-up with entity-bound, unexpired advisory memory.
7. Casual/common conversation with no operational retrieval.
8. New advisory/planning intent.
9. Genuine ambiguity clarification based on top competing candidates.

No broad domain route may override an explicit status/record/meta/action contract. Keywords such as `model`, `source`, `client`, or `research` are signals, never sufficient route decisions by themselves.

## Memory hierarchy

| Layer | Keying | Contents | Rule |
|---|---|---|---|
| Turn context | Request ID | Current message/page metadata | Never persists automatically |
| Session conversation | Session + tenant + surface | Bounded messages/topic | No cross-session module globals |
| Selection memory | Session + list ID | Typed items, source IDs, ordinal map, expiry | Used only by explicit reference/action-target routes |
| Advisory memory | Session + advisory ID/entity | Recommendation, assumptions, risks, summary, expiry/relevance | Never resolves a selection target implicitly |
| Durable project memory | Tenant/project + version | Approved facts/preferences/decisions | Writes require explicit policy and provenance |
| Operational state | Source query ID | Live/report results and freshness | Never treated as durable truth after freshness window |
| Provenance ledger | Session + answer ID | Route, source results, assumptions, confidence, action proof | Read only by meta routes; bounded retention |

## Renderer contracts

Define schemas, then validate before returning text:

- System health: `status`, `evidence[]`, `freshness`, `blockers[]`, `nextAction`.
- Pending approvals: `sourcesChecked[]`, `pendingCount`, `items[]`, `verificationBlockers[]`, `freshness`.
- Research status: `configurationState`, `lastRun`, `evidence[]`, `blockers[]`, `nextAction`.
- Client records: `sourceAttempt`, `count/items` or `exactBlocker`, `freshness`.
- Provenance: `answerId`, `route`, `sources[]`, `liveReads[]`, `assumptions[]`, `confidence`.
- Advisory: `recommendation`, `rationale`, `assumptions[]`, `risks[]`, `nextSafeAction`, optional `sources[]`.
- Action/Ray Review/schedule: structured local draft, resolution state, approval requirement, and `actionProof`.
- Casual: answer only; no Nexus context, operational memory, or source call.
- Fallback: missing field or two plausible intents, never a fixed global menu.

## Source attribution rules

1. Every retrieval returns `sourceId`, type, attempted/succeeded state, retrieved/generated timestamp, freshness class, and error/blocker.
2. “Live” requires a successful request-time read; one successful table cannot hide another failed required table.
3. Static and live items cannot be merged without item-level labels.
4. Report-backed answers name the report and generated timestamp.
5. Assumptions are separate from evidence.
6. Provenance answers use stored trace facts, never reconstructed guesses.

## Governance rules

- Centralize action classes: read-only, local draft, approval-gated write, prohibited.
- Scheduler requests create drafts only; activation needs explicit approval and a receipt.
- Memory writes declare layer, scope, expiry, source, and approval requirement. Durable writes are never incidental side effects of chat.
- Skill creation and persistent rule changes require explicit scoped requests and review.
- Publishing, charging, sending, deployment, destructive DB actions, and live/funded trading remain prohibited or explicit approval-gated.
- Rendered claims must pass a contract validator and side-effect proof validator.

## Regression harness

- Put golden cases in a data file with prompt/transcript, expected route, contract schema, allowed source calls, memory reads/writes, banned phrases, and prohibited effects.
- Inject source adapters and clocks; never require production credentials.
- Test route classification separately from retrieval and rendering.
- Add transcript/state-machine tests for selection/advisory/provenance boundaries.
- Snapshot structured contracts, not prose alone.
- Run a small banned-phrase/unsupported-claim validator across every response.

## Documentation/vault structure

```text
docs/hermes/
  architecture.md
  route_precedence.md
  response_contracts.md
  memory_policy.md
  source_registry.md
  governance.md
tests/hermes/golden/
  prompts.json
  transcripts.json
reports/hermes_brain/
  audit history and generated contract coverage
```

## Implementation phases

1. **Freeze and characterize:** convert this golden suite into data-driven tests; add source/action spies; make no behavior changes.
2. **Contract core:** introduce typed intent candidates, route enum, response schemas, source result schema, and contract validators alongside existing pipeline.
3. **Operational routes:** implement dedicated system health, approvals, research status, client records, opportunity, and provenance handlers using adapters.
4. **Memory isolation:** replace module globals with session/tenant-scoped stores; separate selection/advisory/provenance permissions; align clear-history behavior.
5. **Advisory/casual routes:** move advice and continuity into typed contracts; enforce no-Nexus casual behavior and relevance checks.
6. **Action governance:** unify delegation, Ray Review, scheduling, and action proof under a central policy; keep all external execution disabled until separately approved.
7. **Remove split brain:** migrate or retire legacy intent/response/orchestrator paths only after coverage proves current UI and scripts use the new pipeline.
8. **Verification:** local suite/build, then authenticated browser/Supabase verification, then deployment verification. Each is a separate authorization boundary.

## Acceptance gates

- All golden prompts meet route and contract assertions.
- No deterministic/status/record/safety test calls a model.
- No audit/test activates a scheduler or performs an external/destructive write.
- Two simultaneous sessions cannot see each other's selection, advisory, or trace state.
- Every operational response reports source attempt and freshness or an exact verification blocker.
- Legacy generic `local_status`, allowed-context reasoning text, and fixed fallback menu are unreachable for covered contracts before removal.
