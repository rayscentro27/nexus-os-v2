# Dispute Sandbox Upgrade Plan

Generated: 2026-06-29T16:39:09.287604+00:00

- ok: true
- status: sandbox_plan_ready
- real_disputes_sent: false
- external_action_performed: false
- summary: The next layer is defined for synthetic sandbox proof; every real-send path remains disabled.

## Approval lifecycle

- `{"approval_required": false, "category": "dispute_approval", "client_id": "synthetic_only", "client_visible": true, "created_at": "2026-06-29T16:39:09.286453+00:00", "external_action_performed": false, "id": "dispute-stage-1", "status": "internal_active", "tenant_id": "tenant_demo_goclear", "title": "Synthetic intake"}`
- `{"approval_required": false, "category": "dispute_approval", "client_id": "synthetic_only", "client_visible": true, "created_at": "2026-06-29T16:39:09.286766+00:00", "external_action_performed": false, "id": "dispute-stage-2", "status": "internal_active", "tenant_id": "tenant_demo_goclear", "title": "Document dependency check"}`
- `{"approval_required": true, "category": "dispute_approval", "client_id": "synthetic_only", "client_visible": true, "created_at": "2026-06-29T16:39:09.286773+00:00", "external_action_performed": false, "id": "dispute-stage-3", "status": "ready_for_Ray_review", "tenant_id": "tenant_demo_goclear", "title": "Draft letter preview"}`
- `{"approval_required": true, "category": "dispute_approval", "client_id": "synthetic_only", "client_visible": false, "created_at": "2026-06-29T16:39:09.286777+00:00", "external_action_performed": false, "id": "dispute-stage-4", "status": "approval_gated", "tenant_id": "tenant_demo_goclear", "title": "GoClear compliance review"}`
- `{"approval_required": true, "category": "dispute_approval", "client_id": "synthetic_only", "client_visible": true, "created_at": "2026-06-29T16:39:09.286781+00:00", "external_action_performed": false, "id": "dispute-stage-5", "status": "approval_gated", "tenant_id": "tenant_demo_goclear", "title": "Client approval where required"}`
- `{"approval_required": true, "category": "dispute_approval", "client_id": "synthetic_only", "client_visible": false, "created_at": "2026-06-29T16:39:09.286785+00:00", "external_action_performed": false, "id": "dispute-stage-6", "status": "blocked", "tenant_id": "tenant_demo_goclear", "title": "Sandbox connector proof"}`
- `{"approval_required": true, "category": "dispute_approval", "client_id": "synthetic_only", "client_visible": false, "created_at": "2026-06-29T16:39:09.286788+00:00", "external_action_performed": false, "id": "dispute-stage-7", "status": "blocked", "tenant_id": "tenant_demo_goclear", "title": "Real send"}`
- `{"approval_required": false, "category": "dispute_approval", "client_id": "synthetic_only", "client_visible": true, "created_at": "2026-06-29T16:39:09.286795+00:00", "external_action_performed": false, "id": "dispute-stage-8", "status": "internal_active", "tenant_id": "tenant_demo_goclear", "title": "Proof/event tracking"}`

## Connector plans

- `{"approval_required": true, "id": "certified-mail-sandbox", "live_enabled": false, "mode": "sandbox_proposed", "requirements": ["vendor sandbox account", "sandbox credential stored server-side", "non-deliverable synthetic recipient", "Ray approval", "proof-only request", "legal/compliance review"]}`
- `{"approval_required": true, "id": "internal-email-review", "live_enabled": false, "mode": "local_preview", "requirements": ["rendered preview", "Ray/GoClear review", "no SMTP recipient", "no send call"]}`
