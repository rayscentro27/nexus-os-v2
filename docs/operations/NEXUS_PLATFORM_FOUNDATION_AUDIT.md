# Nexus — Platform Foundation Audit

## Why this exists
We were fixing the same classes of problem tab-by-tab. This audit names the universal systems and
the shared primitives that now back them, so tabs compose foundation instead of reinventing it.

## Repeated patterns found (and the shared primitive that replaces each)
| Repeated pattern | Was | Now (shared primitive) |
|---|---|---|
| "Is this action safe / does it need approval?" logic re-implemented per tab | inline in SourceEntryForm, etc. | `src/config/nexusActionPolicy.ts` |
| Splitting task_requests vs approvals inconsistently | per-tab inserts | `src/lib/nexusRequests.ts` (`submitSourceCapture`) |
| Per-tab Supabase reads | ad-hoc `listTable(...)` everywhere | `src/lib/nexusData.ts` |
| Hermes chat state lost on navigation | local `useState` | `src/lib/hermesChatStore.ts` (`hermesStore`) |
| Hermes panel growing the page | unbounded list | bounded card + internal scroll (Command Center) |
| Status labels invented per tab | strings scattered | `src/config/nexusTabs.ts` + `ActionStatusBadge` |
| Approval visibility ("why didn't it show?") | task_requests-only | `ApprovalVisibilityNote` + linked approvals row |

## Hermes inconsistencies
History reset on navigation, panels could grow the page, review panes were sometimes placeholders.
Fixed for Command Center (persist + scroll) and Source Intake (functional Hermes Review). The store
exposes a reusable API (`hermesStore.getMessages/addMessage/clearHistory/setMode/getMode`).

## Approval / queue inconsistencies
Safe admin capture was wrongly treated as approval-required; review-required items didn't reach
Approvals (root cause: Source Intake wrote `task_requests`, Approvals reads `approvals`). The policy
+ `nexusRequests` now route: safe → owning-tab queue only; review-required → queue **plus** a linked
`approvals` row.

## Status / connection inconsistencies
`nexusTabs.ts` is the single status model (status, statusLabel, dataSources, tables, v1Dependencies,
v2Dependencies, actions, riskLevel, visible, disabledReason, recommendedNextAction). Sidebar badges
+ `TabConnectionStatus` + `SystemStatusOverview` render it.

## Pieces that became shared primitives
`nexusActionPolicy.ts`, `nexusRequests.ts`, `nexusData.ts`, `hermesChatStore.hermesStore`,
`components/common/ActionStatusBadge.tsx` (+ `ApprovalVisibilityNote`).

## Tabs vs the universal model
- **Uses it now:** Source Intake (policy + requests + Hermes Review), Command Center (persistent
  Hermes + scroll + status overview), Approvals (reads approvals; now receives review-required items).
- **Status-labelled (tab level) but per-action policy not yet wired:** Creative Studio, Opportunity
  Lab, GoClear/Apex, Trading Lab, SEO, Integrations, Ops, Events, Model Router. Follow-up: adopt
  `ActionStatusBadge`/`ApprovalVisibilityNote` + `nexusData`/`nexusRequests` where they have actions.
