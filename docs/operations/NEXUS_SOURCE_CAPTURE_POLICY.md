# Nexus — Source Capture Policy (v1)

`source_capture_policy: safe_admin_submitted_capture_v1`

## Rule
A source **Ray/admin submits** that is SAFE does **not** require approval — it goes to the
**Capture Queue** (`task_requests`, `approval_required=false`, `capture_status=queued`). Approval is
required only for risky/uncertain items.

### Safe (auto-queued, no approval)
- Public YouTube video URL (one URL), manual idea, pasted text / transcript.
- Metadata + transcript capture later via the local CLI wrapper; no media download; no external AI;
  no scheduler; no publish/send/trade/deploy; no private/customer data; writes only to v2 intake/
  research/proof tables.

### Requires Ray review (also files an `approvals` row)
Triggers: `uncategorized`, `low_confidence`, `high_compliance_risk`, `risky_destination`,
`client_facing`, `publish_send_trade_deploy`, `scheduler_or_local_command`, `sensitive_data`,
`external_ai_sensitive_text`. In this build: website crawl → `risky_destination`; unknown type →
`uncategorized`; private-looking data → refused/`sensitive_data`.

### Post-capture classification (worker, later)
`auto_routed` · `needs_ray_review` · `parked` · `rejected`.

### Safe destinations (no approval)
Source Intake & Review · Ops & Improvements · Research Only · Knowledge/Memory · Creative Ideas
(draft, not publishing) · Opportunity Lab (candidate only).

### Destinations/actions needing review
client-facing content · GoClear/Apex offer/funnel changes · publish/send/trade/deploy · scheduler ·
raw local/v1 command · external AI on sensitive text.

## Submit behavior
Browser never runs yt-dlp/capture. Safe → Capture Queue + proof event. Review-required → Capture
Queue + `approvals` row + proof. The stored `capture_command_preview` is what a worker runs later.
