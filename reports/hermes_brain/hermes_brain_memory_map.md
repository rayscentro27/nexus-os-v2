# Hermes Brain Memory and Retrieval Map

## Current memory map

| Store / variable | Purpose | Lifetime / expiry | Writes | Reads | Risks | Class |
|---|---|---|---|---|---|---|
| `conversationState.history` | Last user/assistant messages | Module lifetime; capped at 50 messages | Every completed pipeline answer | Exposed by getter; not attached to current context packet | Not session/tenant keyed; UI history persistence differs from brain state | Session/chat |
| `lastListedItems`, `lastRankedList`, `lastRecommendedItem`, `lastSelectedItem`, `lastReferencedItem` | Resolve ordinal/pronoun/entity follow-ups | Module lifetime; cleared only by reset/new list in parts | Retrieval/recommendation/selection helpers | `resolveFollowUp` | Duplicates `selectionMemory`; stale references can persist | Selection |
| `selectionMemory` | Normalized list/rank/recommend/selected state plus active domain | Declares `expiresAfterTurns: 8`, but getter does not enforce turn expiry; `lastUsedAt` is timestamp only | Conversation selection setters | Priority router, eligibility, packet, action/memory routes | Sticky global state; hardcoded opportunities stored instead of live rows; cross-surface/user risk | Selection |
| `AdvisoryContinuityState` | Topic, summary, assumptions, recommendation, risks | Module global; expires after 6 advanced non-neutral turns | After advisory-producing routes | Priority router, context packet, follow-up renderer | Narrow phrase relevance; templates may overwrite nuance; permission mislabeled long-term | Advisory |
| `FallbackContinuityState` | Original ambiguous message and offered options | Module global; 4 turns | Fallback route | Option-reply router and continuation | Static options; accepted reply regex differs from offered labels | Clarification continuity |
| `lastTurnTraceMemory` | Compact previous route/source/model/memory/cost facts | Module global; overwritten each non-trace answer | Pipeline | Context packet for trace-only | Not durable/session keyed; cost/model fields may be null | Provenance |
| `lastRoutingTrace` | Rich last non-trace route decision and action proof | Module global; overwritten by logger | Pipeline | Trace handler | Only latest trace; no source snapshot; cross-user risk | Provenance |
| `lastSupabaseQueryResult` | Table/query/timestamp/rows | Module global until reset | Pipeline after Supabase use | Getter; selection resolution does not consume rows | Pipeline writes empty `rows`, so it cannot support record continuity | Live operational cache |
| `lastIntent`, `lastTopic`, `lastPage`, `lastActionPlan` | Conversation topic continuity | Module lifetime | Non-neutral routes | Domain classifier and diagnostics | Topic is lexical domain, not entity-bound conversational state | Session/chat |
| `hermesChatStore` | Visible message history in local storage | Browser persistent until clear | UI surfaces | UI initialization | Clearing it does not reset module brain memory; role normalization differs (`hermes`/assistant) | UI persistence |
| `getLongTermBusinessContext()` | Hardcoded business priorities/constraints | Static source lifetime | Source code constant | Context packet when long-term allowed | Called memory but not learned/durable; no provenance/freshness | Durable/static context |
| `hermes_second_brain_index_latest.json` via `hermesMemoryContext.ts` | Bounded report-backed recall | Generated report lifetime | External scripts | Legacy/local memory answer helper | Not integrated into main route map; build-time staleness | Durable/report context |
| Page context passed by UI | Page ID, route, visible/selected items/actions | Per call | UI | Page status renderer/context packet | Metadata may be mistaken for verified page/backend state | Session/page |

## Current source and retrieval map

| Source | Type / freshness | Routes | Failure behavior | User attribution / freshness visibility |
|---|---|---|---|---|
| Static `OPPORTUNITIES` in pipeline | Static hardcoded | Opportunity retrieval, recommendations, selection | Always available even if live read fails | Labeled static fallback, but items are not individually sourced or dated |
| `getLongTermBusinessContext` | Static hardcoded | Advisory/revenue/local planning | Silently absent only by policy | Usually described generically; no date |
| Supabase authenticated client | Live read at request time | Approvals, clients, opportunities, monetization, research inventory, revenue | Config missing, no session, RLS/table query errors; partial success allowed | Live label and request timestamp returned internally; partial/freshness detail not consistently rendered |
| `approvals` + Ray Review `task_requests` | Live Supabase | Pending approvals | Counts/status/title normalization; errors appended | Best current attribution; no `updated_at` freshness summary |
| `business_opportunities` / `monetization_opportunities` | Live Supabase plus static list | Inventory/revenue | Generic rows or static fallback | Source mode labeled, not row-level provenance |
| `client_profiles` | Live Supabase | Protected client inventory variants | Exact configure/auth/RLS message from live context; otherwise generic client missing-context text | Live source label only if route actually reads |
| `research_sources` / `research_runs` | Live Supabase | Explicit research inventory | Generic summaries; research status route often never reads | No dedicated engine-state/freshness renderer |
| `system_health` Supabase table | Potential live source | Live context only when a retrieval route calls it | Not used by dedicated local health renderer | Dedicated health says local checkpoint, not table freshness |
| `reportRegistry` and imported JSON/Markdown reports | Derived build-time snapshots | Report inventory, activity, specialized adapters | Missing/static entries or generic local status | Paths sometimes shown; generated-at handling is fragmented |
| `systemHealthData`, section registry | Static/derived UI context | UI/system health summary | Returns bundled status | Partial source labeling; hardcoded build checkpoint dominates |
| Research/YouTube data modules and reports | Static/derived | UI and older adapters | Not consistently connected to main status route | Freshness varies by file and is not normalized |
| Page/website metadata | Per-request UI metadata | Page connection/context | Explicitly says metadata unavailable when absent | Contract distinguishes metadata from live backend, which is appropriate |
| Activity journal | Local browser/module data | Activity summaries | Uses confirmed checkpoint wording | User gets broad source label; persistence/freshness varies |
| Routing trace | Derived runtime record | Provenance/meta | Says no prior trace when absent | Strong route/source summary; no durable history |
| Model provider / `hermes-chat` edge function | Live external inference if configured | `model_reasoning` | Configuration or provider failure returns safe local/error text | Provider/model metadata tracked; not needed for most routes |
| Hardcoded fallback text | Assumption/template | Local reasoning, fallback, action/schedule | Always returns text | Often source list is `none`, `local_context`, or policy name; assumptions are not explicit |

## Boundary conclusions

- Selection and advisory memory are physically separate, but policy types are not separate: advisory and fallback are attached whenever `longTermMemory` is allowed.
- Session memory is not keyed by session, user, tenant, or chat surface.
- Durable memory is mostly static source and generated reports, not an explicit durable memory service.
- Live operational state should never be stored as advisory or selection truth; the current pipeline partly follows this but fails to preserve live retrieved entities.
- Provenance memory is one-turn-only and should become a bounded, session-keyed trace ledger with source IDs, timestamps, success/error state, assumptions, and confidence.
