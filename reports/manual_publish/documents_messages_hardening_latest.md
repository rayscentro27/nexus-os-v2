# Documents and Messages Hardening

Generated: 2026-06-29T16:39:09.103965+00:00

- ok: true
- status: schema_hardened_storage_pending
- document_requirements: 6
- document_records: 6
- message_threads: 2
- message_records: 2
- real_upload_enabled: false
- external_messages_sent: false
- storage_blocker: private bucket plus tenant/client RLS and retention/security review
- external_action_performed: false

## Document requirements

- `{"approval_required": false, "automation_level": "client_visible_safe", "category": "documents", "client_id": "client_demo_001", "client_visible": true, "created_at": "2026-06-29T16:39:09.101298+00:00", "goclear_review_status": "pending", "id": "doc-req-id", "priority": "medium", "recommended_next_action": "Complete the listed portal step.", "risk_level": "low", "sensitive": true, "source": "same_day_operations_activation", "status": "missing", "summary": "Government identity verification", "tenant_id": "tenant_demo_goclear", "title": "Government identity verification"}`
- `{"approval_required": false, "automation_level": "client_visible_safe", "category": "documents", "client_id": "client_demo_001", "client_visible": true, "created_at": "2026-06-29T16:39:09.101683+00:00", "goclear_review_status": "pending", "id": "doc-req-address", "priority": "medium", "recommended_next_action": "Complete the listed portal step.", "risk_level": "low", "source": "same_day_operations_activation", "status": "missing", "summary": "Current address proof", "tenant_id": "tenant_demo_goclear", "title": "Current address proof"}`
- `{"approval_required": false, "automation_level": "client_visible_safe", "category": "documents", "client_id": "client_demo_001", "client_visible": true, "created_at": "2026-06-29T16:39:09.101727+00:00", "goclear_review_status": "pending", "id": "doc-req-formation", "priority": "medium", "recommended_next_action": "Complete the listed portal step.", "risk_level": "low", "source": "same_day_operations_activation", "status": "approved", "summary": "Formation documents", "tenant_id": "tenant_demo_goclear", "title": "Formation documents"}`
- `{"approval_required": false, "automation_level": "client_visible_safe", "category": "documents", "client_id": "client_demo_001", "client_visible": true, "created_at": "2026-06-29T16:39:09.101759+00:00", "goclear_review_status": "pending", "id": "doc-req-ein", "priority": "medium", "recommended_next_action": "Complete the listed portal step.", "risk_level": "low", "source": "same_day_operations_activation", "status": "approved", "summary": "EIN confirmation", "tenant_id": "tenant_demo_goclear", "title": "EIN confirmation"}`
- `{"approval_required": false, "automation_level": "client_visible_safe", "category": "documents", "client_id": "client_demo_001", "client_visible": true, "created_at": "2026-06-29T16:39:09.101769+00:00", "goclear_review_status": "pending", "id": "doc-req-bank", "priority": "medium", "recommended_next_action": "Complete the listed portal step.", "risk_level": "low", "sensitive": true, "source": "same_day_operations_activation", "status": "under_review", "summary": "Three months business bank statements", "tenant_id": "tenant_demo_goclear", "title": "Three months business bank statements"}`
- `{"approval_required": false, "automation_level": "client_visible_safe", "category": "documents", "client_id": "client_demo_001", "client_visible": true, "created_at": "2026-06-29T16:39:09.101778+00:00", "goclear_review_status": "pending", "id": "doc-req-revenue", "priority": "medium", "recommended_next_action": "Complete the listed portal step.", "risk_level": "low", "source": "same_day_operations_activation", "status": "missing", "summary": "Current revenue summary", "tenant_id": "tenant_demo_goclear", "title": "Current revenue summary"}`

## Message templates

- `{"approval_required": false, "automation_level": "client_visible_safe", "category": "client_message", "client_id": "client_demo_001", "client_visible": true, "created_at": "2026-06-29T16:39:09.101927+00:00", "external_message_sent": false, "goclear_review_status": "pending", "id": "safe-msg-1", "priority": "medium", "recommended_next_action": "Complete the listed portal step.", "risk_level": "low", "source": "same_day_operations_activation", "status": "open", "summary": "Your readiness record is under review. Complete missing document tasks; nothing has been submitted externally.", "tenant_id": "tenant_demo_goclear", "thread_id": "thread-review", "title": "GoClear review update"}`
- `{"approval_required": false, "automation_level": "client_visible_safe", "category": "client_message", "client_id": "client_demo_001", "client_visible": true, "created_at": "2026-06-29T16:39:09.101976+00:00", "external_message_sent": false, "goclear_review_status": "pending", "id": "safe-msg-2", "priority": "medium", "recommended_next_action": "Complete the listed portal step.", "risk_level": "low", "source": "same_day_operations_activation", "status": "open", "summary": "Current address proof and a revenue summary are still required. Upload remains unavailable until private storage and RLS are approved.", "tenant_id": "tenant_demo_goclear", "thread_id": "thread-docs", "title": "Documents needed"}`
