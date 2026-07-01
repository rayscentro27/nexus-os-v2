# Hermes Restriction Audit

Generated: 2026-06-30

## Principle

Hermes should be context-capable but execution-restricted. Safe reads and recommendations are allowed. External actions, persistent writes, money movement, tenant-sensitive access, deployment, and trading remain blocked or approval-gated.

## A. Must keep permanently

| Restriction | Current location | Why | Blocks | Decision | Next implementation |
|---|---|---|---|---|---|
| No service-role/API/model secrets in frontend | `src/lib/hermesSupabaseContextAdapter.ts`, `.gitignore` | Browser secrets bypass tenant boundaries | execution/security | remain | Use authenticated server route only |
| No RLS weakening or tenant bypass | Supabase policies; unchanged by this task | Preserves tenant isolation | execution/security | remain | Test tenant-scoped reads before any adapter |
| No direct sends, publishing, charges, disputes, client inserts, deploys, or live trades | `hermesResponseRouter.ts`, high-risk guards | Irreversible/external impact | execution | remain approval-gated | Route proposals to Ray Review; never execute from chat |
| No Oanda live endpoint or funded trading | Trading guards/router | Real-money risk | execution | remain | Paper/demo read summaries only |
| No destructive SQL/filesystem operations | CLI policy and UI gates | Irreversible data loss | execution | remain | Read-only inspection or reviewed runbook only |

## B. Safe to loosen with read-only context

| Restriction | Current location | Why it existed | Blocks | Decision | Next implementation |
|---|---|---|---|---|---|
| Approved report content limited to viewer | `reportRegistry.js`, `ReportCenter.jsx` | No shared contract | context | loosened | Refresh registry during approved build pipeline |
| Report metadata/selected report unavailable to Hermes | `hermesReportContextAdapter.ts` | Missing adapter | conversation/context | loosened | Pass selected report identifier with chat context |
| System, blocker, approval, offer, opportunity, scheduler and paper-trading summaries were canned | `hermesBackendContextAdapter.ts` | Router had isolated handlers | conversation/context | loosened | Replace bundled summaries with authenticated read endpoint when proven |
| Activity memory is browser-local | `hermesActivityJournal.ts`, `hermesMemoryQuery.ts` | No durable safe store | context | keep local but readable | Add tenant-scoped durable memory later |
| Safe Supabase/RLS summaries unavailable | `hermesSupabaseContextAdapter.ts` | No tenant-scoped endpoint contract | context | safe to loosen, not yet wired | Add authenticated allow-listed aggregate endpoint |

## C. Future adapter needed

| Restriction | Current location | Blocks | Decision | Recommended next step |
|---|---|---|---|---|
| No real model/LLM reasoning | `hermesBackendContextAdapter.ts` | conversation/reasoning | future adapter | Server-side model gateway with redaction and audit logging |
| No web research | backend adapter status | context | future adapter | Approval-gated research task with citations |
| No Deep Agents/Ollama worker | none installed | reasoning/work delegation | future adapter | Defer until context/auth contracts are stable |
| No durable cross-device memory | localStorage journal | context | future adapter | Tenant-scoped append/read API with retention controls |
| No server-side Supabase service queries | Supabase stub | context | future adapter | Authenticated Netlify/server endpoint with allow-listed summaries; never expose service key |

## Current access source matrix

| Source | Used by Hermes | Live/static | Safe | Location | Limitation | Next fix |
|---|---|---|---|---|---|---|
| Browser `Date()` | yes | live client time | yes | `hermesTimeContext.ts` | Client clock only | Optional trusted server time |
| Page context/visible items | yes | current UI + bundled rows | yes | `hermesContextBridge.ts` | Only passed/known items | Expand typed page bridges |
| Local bundled Nexus context | yes | static | yes | `hermesBackendContextAdapter.ts`, data modules | Can become stale | Stamp all snapshots |
| localStorage activity memory | yes | live browser-local | yes | `hermesActivityJournal.ts`, `hermesMemoryQuery.ts` | Not durable/cross-device | Tenant-scoped durable adapter |
| Approved reports/metadata | yes | static generated snapshot | yes | `reportRegistry.js`, `hermesReportContextAdapter.ts` | Build-time freshness | Authenticated report API later |
| Supabase client | no Hermes query | unavailable | unsafe without scoped contract | `hermesSupabaseContextAdapter.ts` | No Hermes endpoint; service role forbidden | Add anon/RLS or backend aggregate route |
| Backend/API | contract only | static local adapter | yes | `hermesBackendContextAdapter.ts` | No network backend endpoint | Add authenticated endpoint after tenancy design |
| Model/LLM | no | unavailable | n/a | backend status | No real reasoning model | Future server-side gateway |
| Web | no | unavailable | n/a | backend status | No search/citations | Future approval-gated research adapter |

## Result

Hermes now has a typed safe read-only foundation for approved report snapshots and bundled operational summaries. It still performs no backend network query. All returned context identifies source type, freshness, limitations, safety level, and whether execution requires approval.
