# Hermes Message History Audit

**Generated:** 2026-07-01
**Status:** Baseline audit — routing trace facility added

## Summary

| Metric | Value |
|--------|-------|
| Total messages audited | 12 |
| Correctly routed | 0 (no trace existed) |
| Failed routing | 0 (no trace existed) |
| Not logged | 12 |

All messages are scored as "not_logged" because the routing trace facility (`hermesRoutingTrace.ts`) did not exist before this audit. The trace facility has been added to capture routing decisions going forward.

## Message Stores Found

### 1. hermesChatStore (localStorage)
- **Key:** `nexus_hermes_chat_history`
- **Max:** 50 messages
- **Used by:** HermesChatPanel, HermesInlineDrawer
- **Logged:** role, text, meta
- **NOT logged:** intent, route, source, modelUsed, supabaseUsed, followupMemoryUsed, safetyGateUsed

### 2. hermesActivityJournal (localStorage)
- **Key:** `nexus_hermes_activity_journal`
- **Max:** 500 events
- **Used by:** HermesChatPanel, HermesInlineDrawer, recordActivity()
- **Logged:** source, pageId, route, eventType, title, summary, status, dataSource, safetyLevel
- **NOT logged:** intent, selectedRoute, modelUsed, supabaseUsed, followupMemoryUsed, safetyGateUsed

### 3. hermesModelUsageLedger (localStorage)
- **Key:** `nexus-hermes-model-usage-v1`
- **Max:** 200 entries
- **Used by:** hermesModelChat, logModelAttempt, logModelSkipped
- **Logged:** route, modelProvider, modelName, promptType, tokens, wasModelCalled, skippedReason
- **NOT logged:** userMessage, hermesAnswer, intent, supabaseUsed, followupMemoryUsed

### 4. hermesConversationState (in-memory session)
- **Key:** none (module-level, not persisted)
- **Max:** 50 messages
- **Used by:** hermesBrainPipeline, hermesReasoningEngine
- **Logged:** history, lastListedItems, lastRankedList, lastRecommendedItem, lastSelectedItem
- **NOT logged:** activationLevel, intent, route, source, safetyGateUsed

### 5. hermesRoutingTrace (localStorage) — NEW
- **Key:** `nexus-hermes-routing-trace-v1`
- **Max:** 100 entries
- **Used by:** hermesBrainPipeline (new), hermesRoutingTrace
- **Logged:** message, surface, page, activationLevel, intent, sourceDecision, route, modelRoute, usedSupabase, usedModel, usedMemory, selectedEntity, safetyGate, answerBuilder, fallbackReason, confidence
- **NOT logged:** secrets, full PII, sensitive client details

## Canonical Message Audit

| # | Message | Expected Level | Expected Source | Failure Type | Fix Needed |
|---|---------|---------------|-----------------|-------------|------------|
| 1 | What business opportunities are available? | L2: Supabase | live_supabase | not_logged | Query live Supabase business_opportunities, store in memory |
| 2 | Which one do you recommend? | L3: Memory | conversation_memory | not_logged | Resolve from last listed, rank, store ranked list, recommend |
| 3 | Ok pick one for us to review. | L3: Memory | conversation_memory | not_logged | Select recommended item from memory, present for review |
| 4 | So number 3 how do we implement? | L3: Memory | conversation_memory | not_logged | Resolve "number 3" from ranked list, then L4 implementation plan |
| 5 | The monthly readiness subscription. | L3: Memory | conversation_memory | not_logged | Named entity match against listed items |
| 6 | Are you connected to live Supabase data? | L1: Meta | local_capability | not_logged | Use 5-state Supabase access state |
| 7 | What did you do today? | L1: Meta | daily_translator | not_logged | Use daily translator, not raw log |
| 8 | Give me the CEO version. | L1: Meta | ceo_translator | not_logged | Use CEO summary translator |
| 9 | What model are you using? | L1: Meta | usage_ledger | not_logged | Use model usage ledger |
| 10 | Can you place a trade? | L0: Safety | safety_gate | not_logged | Block with safety gate |
| 11 | Is YouTube research running? | L1: Meta | local_reports | not_logged | Operations status answer |
| 12 | What business should I start in 30 days? | L4: Reasoning | supabase+memory | not_logged | Strategy/recommendation, not section status |

## Key Finding

**No routing trace existed before this audit.** Every message was processed without logging:
- Which activation level was used
- Which intent was detected
- Which source was used
- Whether Supabase was queried
- Whether the model was called
- Whether conversation memory was used
- Whether the safety gate was triggered

The `hermesRoutingTrace.ts` facility has been added to capture all of this going forward.
