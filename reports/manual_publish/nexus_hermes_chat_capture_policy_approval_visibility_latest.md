# Nexus — Hermes Persistence + Capture Policy + Approval Visibility (report)

- generated_at: 2026-06-25 · build PASS · watch PASS

## 1. Why the earlier request didn't show in Approvals
**Table mismatch.** Source Intake wrote to `task_requests`; the Approvals tab (`ApprovalCenter`)
reads the `approvals` table (`listTable('approvals')`). The row existed (visible via the Capture
Queue) but was never queried by Approvals. Not RLS, not a status filter.

## 2. Capture policy fix
Safe admin-submitted capture (public YouTube URL / idea / transcript) now becomes a **Capture Queue**
item in `task_requests` with `approval_required=false`, `capture_status=queued`,
`source_capture_policy=safe_admin_submitted_capture_v1` — **no approval, no Approvals clutter**.
Message: "Queued for safe capture — Ray approval is only required if Nexus cannot categorize the
source or if the next action is risky." No browser capture, no yt-dlp in browser.

## 3. When approval is still required
`uncategorized`, `low_confidence`, `high_compliance_risk`, `risky_destination`, `client_facing`,
`publish_send_trade_deploy`, `scheduler_or_local_command`, `sensitive_data`,
`external_ai_sensitive_text`. This build flags: website crawl → `risky_destination`; unknown type →
`uncategorized`; private-looking data → refused. Publish/send/trade/deploy gates unchanged.

## 4. Review-required items now appear in Approvals
Review-required submits also call `createApproval` → inserts an `approvals` row (status `pending`,
`item_type` e.g. `risky_destination_review`/`uncategorized_source_review`, payload has
`task_request_id` + source URL + trigger). `ApprovalCenter` reads `approvals` → it shows. Verified by
code path (Approvals reads `approvals`; createApproval inserts there) — no test rows created to keep
Approvals clean.

## 5. Capture Queue visible in Source Intake
Yes — the right-rail "Capture Queue" lists `task_requests` capture items: title/URL, **Safe capture**
vs **Approval required**, review trigger, command preview, next step ("Waiting for local runner" /
"Needs Ray review in Approvals"). Relabeled from "Pending Approval".

## 6–8. Hermes chat
- **Persists** across tab changes + reloads via `localStorage` (`nexus_hermes_chat_history`,
  `nexus_hermes_mode`; last 50; sensitive text never stored). Lazy-init + `useEffect` save.
- **Scrolls internally**: Hermes card bounded `min(64vh,720px)`; message list `overflow-y:auto`;
  composer pinned and always visible; auto-scroll to latest. Page no longer grows from chat.

## 9. Hermes approval authority
Copy added: "Hermes can recommend, but Ray approves risky actions." Hermes may recommend/explain/
create task_requests/draft recommendations/auto-route safe research; it must NOT directly approve
publish/send/trade/deploy/scheduler/raw command/external-AI-on-sensitive-text.

## Safety
build PASS · watch PASS · no capture · no scheduler · v1 untouched · no publish/send/trade/deploy ·
no external AI · approval `13eafcab` pending · FB `publish_enabled` false · no secrets · `.env` not
committed · no schema/RLS change · approval gates intact.

## Next
Build the approved-capture worker (poll queued safe + approved review items → run the CLI wrapper
once → write research_sources/transcript_reviews + proof) and an Approvals-UI "approve & queue"
button for review-required source items.
