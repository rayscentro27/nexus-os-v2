# Nexus — Platform Foundation (report)

- generated_at: 2026-06-25 · build PASS · watch PASS

## Universal primitives added
- **`src/config/nexusActionPolicy.ts`** — categories, risk triggers, outcomes, helpers
  (`classifyCaptureSubmission`, `getApprovalRequirement`, `shouldShowInApprovals`,
  `getActionStatusLabel`, etc.) + universal copy. The single source of truth for "safe vs review vs
  approval vs disabled."
- **`src/lib/nexusRequests.ts`** — `submitSourceCapture`: files `task_requests` for safe work and a
  **linked `approvals` row** for review-required work + a `nexus_events` proof. Used by Source Intake.
- **`src/lib/nexusData.ts`** — thin typed safe-read layer (approvals, task_requests, agent_jobs,
  nexus_events, system_health, research_sources, intake_events, transcript_reviews, creative_assets,
  social_posts, model_routes/providers).
- **`src/lib/hermesChatStore.ts`** extended with `hermesStore` (getMessages/addMessage/clearHistory/
  setMode/getMode) — reusable persistent Hermes state.
- **`src/components/common/ActionStatusBadge.tsx`** (+ `ApprovalVisibilityNote`) — universal status
  badge + approval-visibility note, policy-driven.

## Tabs refactored to use the foundation
- **Source Intake** — `SourceEntryForm` now calls `submitSourceCapture` (policy decides safe-queue vs
  review); `ReviewDetailPanel` (Hermes Review) shows approval-needed + reason via the policy.
- **Command Center** — persistent Hermes (store) + internal-scroll chat + `SystemStatusOverview`
  (compact) already in place; approval-authority copy shown.
- **Approvals** — unchanged reader; now receives review-required source items via the linked-approval
  path.

## Tabs still needing follow-up (status-labelled, per-action policy not yet wired)
Creative Studio, Opportunity Lab, GoClear/Apex, Trading Lab, SEO, Integrations, Ops, Events, Model
Router. They already carry correct tab-level status labels; next is to adopt `ActionStatusBadge`/
`ApprovalVisibilityNote` + `nexusData`/`nexusRequests` where they have real actions.

## Why the earlier Source Intake request didn't show in Approvals
Table mismatch: Source Intake wrote `task_requests`; Approvals reads `approvals`. Fixed via the
universal model — safe work stays in the owning queue; review-required work files a linked approvals
row (`createApproval` → `approvals`, status pending).

## Hermes persistence + scroll
Persists across tab changes + reloads via localStorage (last 50 msgs; sensitive text never stored).
Chat scrolls inside a bounded card (`min(64vh,720px)`, `overflow-y:auto`); composer pinned/visible.

## Still not connected
Capture worker (documented as next; NOT built). Per-action policy wiring on the non-Source-Intake
tabs. Public search provider (Hermes search) not deployed.

## Safety
build PASS · watch PASS · no capture/worker · no scheduler · v1 untouched · no publish/send/trade/
deploy · no external AI · FB `publish_enabled` false · no secrets · `.env` not committed · no
schema/RLS change · approval gates intact.

## Next build recommendation
Build the **approved-capture worker** (poll queued-safe + approved review `task_requests` → run the
stored CLI command once → write research_sources/transcript_reviews + proof → set `done`), then roll
`ActionStatusBadge`/`nexusData`/`nexusRequests` into the remaining tabs.
