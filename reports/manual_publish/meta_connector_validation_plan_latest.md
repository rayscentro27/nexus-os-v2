# Meta Connector Validation Plan

Generated: 2026-06-29T16:39:09.460471+00:00

- ok: true
- status: connector_config_present_validation_pending
- raw_values_included: false
- network_validated: false
- publish_enabled: false
- drafts_created: 5
- ray_review_required: true
- safe_validation_command: Use a separately approved read-only Graph API /me/accounts request with token redaction.
- external_action_performed: false
- summary: Prepared Meta read-only validation and five $97 drafts; no network call or post occurred.

## Plan

- **id:** meta-validation-plan
- **connector:** Meta Graph API
- **configured_by_key_presence:** True
- **key_presence:** {"META_APP_ID": true, "META_APP_SECRET": true, "META_PAGE_ACCESS_TOKEN": true, "META_PAGE_ID": true, "VITE_META_IG_ACCOUNT_ID": true, "VITE_META_PAGE_ACCESS_TOKEN": true, "VITE_META_PAGE_ID": true}
- **raw_values_included:** False
- **network_validated:** False
- **safe_validation_request:** GET /me/accounts?fields=id,name (read-only, separately approved; never log token)
- **sandbox_test_requirements:** ["Ray selects owned test page/account", "confirm token scope and expiry", "read-only identity check", "approve exact unpublished/test post design", "retain publish gate"]
- **publish_enabled:** False
- **approval_required:** True

## Drafts

- `{"approval_required": true, "automation_level": "approval_required", "category": "social_draft", "client_id": "synthetic_marketing_only", "client_visible": false, "created_at": "2026-06-29T16:39:09.457664+00:00", "id": "social-readiness-1", "priority": "high", "public_content_published": false, "risk_level": "medium", "status": "ready_for_Ray_review", "summary": "Draft-only educational post: Know your funding blockers before applying. Request a GoClear $97 Funding Readiness Review to identify next steps; outcomes are not guaranteed.", "tenant_id": "tenant_demo_goclear", "title": "Know your funding blockers before applying"}`
- `{"approval_required": true, "automation_level": "approval_required", "category": "social_draft", "client_id": "synthetic_marketing_only", "client_visible": false, "created_at": "2026-06-29T16:39:09.458654+00:00", "id": "social-readiness-2", "priority": "high", "public_content_published": false, "risk_level": "medium", "status": "ready_for_Ray_review", "summary": "Draft-only educational post: The $97 Readiness Review explained. Request a GoClear $97 Funding Readiness Review to identify next steps; outcomes are not guaranteed.", "tenant_id": "tenant_demo_goclear", "title": "The $97 Readiness Review explained"}`
- `{"approval_required": true, "automation_level": "approval_required", "category": "social_draft", "client_id": "synthetic_marketing_only", "client_visible": false, "created_at": "2026-06-29T16:39:09.458680+00:00", "id": "social-readiness-3", "priority": "high", "public_content_published": false, "risk_level": "medium", "status": "ready_for_Ray_review", "summary": "Draft-only educational post: Three documents that slow funding readiness. Request a GoClear $97 Funding Readiness Review to identify next steps; outcomes are not guaranteed.", "tenant_id": "tenant_demo_goclear", "title": "Three documents that slow funding readiness"}`
- `{"approval_required": true, "automation_level": "approval_required", "category": "social_draft", "client_id": "synthetic_marketing_only", "client_visible": false, "created_at": "2026-06-29T16:39:09.458695+00:00", "id": "social-readiness-4", "priority": "high", "public_content_published": false, "risk_level": "medium", "status": "ready_for_Ray_review", "summary": "Draft-only educational post: Business profile consistency check. Request a GoClear $97 Funding Readiness Review to identify next steps; outcomes are not guaranteed.", "tenant_id": "tenant_demo_goclear", "title": "Business profile consistency check"}`
- `{"approval_required": true, "automation_level": "approval_required", "category": "social_draft", "client_id": "synthetic_marketing_only", "client_visible": false, "created_at": "2026-06-29T16:39:09.458709+00:00", "id": "social-readiness-5", "priority": "high", "public_content_published": false, "risk_level": "medium", "status": "ready_for_Ray_review", "summary": "Draft-only educational post: Why readiness comes before applications. Request a GoClear $97 Funding Readiness Review to identify next steps; outcomes are not guaranteed.", "tenant_id": "tenant_demo_goclear", "title": "Why readiness comes before applications"}`
