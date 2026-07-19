# Nexus OS 3.0 — Wave 4A.3 Advisory Context Ownership

Generated: 2026-07-19

## 1. Starting checkpoint

- Branch: `main`
- Starting HEAD: `a82cb1d5e24dcb1a9885d42a8c028ffe47054460`
- Starting commit: `document hermes production workroom verification`
- Production state at start: previous Wave 4A.2 Workroom production verification was documented against the deployed site.

## 2. Worktree safety

The repository still contained unrelated dirty runtime, Alpha, Telegram, report, cache, and temporary files before this repair. Wave 4A.3 edits were kept to Hermes advisory-context code, focused tests, Capability OS records, and Wave 4A.3 reports. No destructive git command was used.

## 3. Current memory-flow audit

The canonical Workroom path was:

```text
HermesChatPanel
  -> runHermesConversation
  -> classifyHermesConversationMode
  -> resolveHermesMemory
  -> resolveHermesReference
  -> generateHermesResponse
  -> updateHermesSessionAfterResponse
  -> normalizeHermesWorkroomResponse
```

The stale-context failure was not caused by the Workroom render path. The renderer was already using normalized schema-v2 messages from Wave 4A.1/4A.2.

## 4. Root cause

`answerRevenueAction()` and `answerBiggestOperatingRisk()` produced correct visible text, but both attached the generic priority advisory context from `buildOperatingContextAdvisory()`. That context was built from `context.priorities`, whose preferred recommendation remained `Client live-data flag off`.

Result:

```text
Ray: how can we make money today?
Hermes: $97 readiness review journey
Stored advisory context: today_operating_priorities / Client live-data flag off
Ray: why that one?
Hermes follow-up resolved against Client live-data flag off
```

## 5. Canonical advisory contract

Wave 4A.3 added structured advisory fields:

- `topicId`
- `topicLabel`
- `topicType`
- `sourceIntent`
- `sourceResponseStrategy`
- `recommendation`
- `alternatives`
- `status`
- `supersedesAdvisoryId`

The canonical recommendation now carries rationale, feasibility, risks, blockers, dependencies, next step, and evidence IDs.

## 6. Active-context ownership

The Hermes session now maintains:

- `activeAdvisoryId`
- bounded `advisoryHistory`
- active advisory context
- selection context

New recommendation-producing `EXECUTIVE_ADVICE` responses create a new advisory context, mark the previous active context `SUPERSEDED`, and set the new advisory ID active. Follow-up, status, greeting, and action-preparation responses do not replace active advisory context.

## 7. Topic-switch rules

Recommendation-producing context now switches by produced advisory metadata, not by P0-P4 rank. Priority, risk, and revenue responses each create separate advisory contexts:

- `EXECUTIVE_PRIORITY`
- `EXECUTIVE_RISK`
- `REVENUE_ACTION`

P0-P4 still affects priority ranking, but no longer owns conversational reference resolution after a newer recommendation is produced.

## 8. Explicit older-topic handling

`resolveHermesMemory()` can resolve explicit older-topic references from bounded advisory history. Example:

```text
going back to the client live-data flag, what would stop us?
```

This resolves to the older priority topic for that turn without permanently reactivating stale context.

## 9. Follow-up semantic mapping

Follow-ups now read the correct structured field:

- `why that one?` -> rationale
- `is that realistic?` -> feasibility
- `what would stop us?` -> blockers and dependencies
- `go deeper` / numbered reference -> deep-dive
- `turn that into a task` -> selected recommendation through governed draft only

## 10. Persistence behavior

Recommendation-producing Workroom messages now include serializable advisory metadata. On refresh, `HermesChatPanel` seeds the canonical session from the latest valid persisted advisory context. Functions and callbacks are still never stored.

## 11. Observability

Conversation traces now include:

- `activeAdvisoryIdBefore`
- `activeAdvisoryIdAfter`
- `resolvedAdvisoryId`
- `resolutionMethod`
- `topicSwitched`
- `supersededAdvisoryId`
- `followUpSemantic`

## 12. Unit certification

Passed:

- `tests/hermes_advisory_context_ownership.test.ts`
- `tests/hermes_production_intent_differentiation.test.ts`
- `tests/hermes_conversation_engine.test.ts`
- `tests/hermes_live_workroom_contract.test.ts`
- Full unit suite: 94 files / 1476 tests

## 13. Local browser certification

Passed against local production build:

- `tests/e2e/hermes-advisory-context-certification.spec.ts`: 2/2
- `tests/e2e/hermes-production-intent-certification.spec.ts` + `tests/e2e/hermes-live-workroom-certification.spec.ts`: 14/14

## 14. Live production certification

Pending until this commit is pushed and the production deployment is verified. Capability health remains degraded for `hermes_advisory_context_production_certification` until live production passes after deployment.

## 15. Security

- No external framework installed.
- No database migration added.
- No credential values stored.
- No function/callback persistence added.
- Alpha Supabase access remains prohibited.
- Stripe remains test-only/deferred for live activation.
- Live trading remains blocked by policy.
- Ordinary questions still create no work; explicit task requests create governed conversation-only draft actions.

## 16. Limitations

- Durable cross-session advisory resumption remains intentionally bounded. A new session should not inherit stale prior-day advisory context automatically.
- Live production certification requires deployed commit verification after push.

## 17. Department Operations readiness

Local certification supports moving toward Department Operations only after live production advisory-context certification passes with zero stale-topic leakage, zero page errors, and zero console errors.
