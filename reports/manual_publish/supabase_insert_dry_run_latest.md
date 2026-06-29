# Supabase Insert Dry Run

Generated: 2026-06-29T17:34:16.203131+00:00

- ok: true
- status: dry_run_passed
- files_validated: 24
- records_validated: 131
- invalid_records: 0
- projection_only: true
- default_tenant: tenant_demo_goclear
- live_insertion_performed: false
- service_role_used: false
- next_required_action: Review projected legacy UUID mappings and tenant defaults before a separately approved execution runner.
- external_action_performed: false

## Validations

- `{"file": "client_profiles_latest.json", "missing_fields": [], "projection_transformations": ["id_mapped_to_external_id"], "records": 1, "table": "client_profiles", "valid": true}`
- `{"file": "client_tasks_latest.json", "missing_fields": [], "projection_transformations": [], "records": 4, "table": "client_tasks", "valid": true}`
- `{"file": "client_documents_latest.json", "missing_fields": [], "projection_transformations": [], "records": 6, "table": "client_documents", "valid": true}`
- `{"file": "credit_profile_readiness_scores_latest.json", "missing_fields": [], "projection_transformations": [], "records": 1, "table": "readiness_scores", "valid": true}`
- `{"file": "business_profile_readiness_scores_latest.json", "missing_fields": [], "projection_transformations": [], "records": 1, "table": "readiness_scores", "valid": true}`
- `{"file": "funding_readiness_scores_latest.json", "missing_fields": [], "projection_transformations": [], "records": 1, "table": "funding_readiness_scores", "valid": true}`
- `{"file": "credit_repair_workflow_latest.json", "missing_fields": [], "projection_transformations": [], "records": 3, "table": "credit_workflow_items", "valid": true}`
- `{"file": "dispute_workflow_test_latest.json", "missing_fields": [], "projection_transformations": [], "records": 5, "table": "dispute_cases", "valid": true}`
- `{"file": "dispute_letter_drafts_latest.json", "missing_fields": [], "projection_transformations": [], "records": 5, "table": "dispute_letter_drafts", "valid": true}`
- `{"file": "business_profile_requirements_latest.json", "missing_fields": [], "projection_transformations": [], "records": 14, "table": "business_profile_requirements", "valid": true}`
- `{"file": "business_opportunities_latest.json", "missing_fields": [], "projection_transformations": ["id_mapped_to_external_id"], "records": 10, "table": "business_opportunities", "valid": true}`
- `{"file": "partner_offers_latest.json", "missing_fields": [], "projection_transformations": ["id_mapped_to_external_id", "tenant_id_defaulted_for_internal_export"], "records": 20, "table": "partner_offers", "valid": true}`
- `{"file": "approval_cards_latest.json", "missing_fields": [], "projection_transformations": ["tenant_id_defaulted_for_internal_export"], "records": 13, "table": "approval_cards", "valid": true}`
- `{"file": "admin_review_queue_latest.json", "missing_fields": [], "projection_transformations": [], "records": 8, "table": "admin_review_queue", "valid": true}`
- `{"file": "approved_client_guidance_latest.json", "missing_fields": [], "projection_transformations": [], "records": 8, "table": "approved_client_guidance", "valid": true}`
- `{"file": "client_questions_latest.json", "missing_fields": [], "projection_transformations": [], "records": 1, "table": "client_questions", "valid": true}`
- `{"file": "client_escalations_latest.json", "missing_fields": [], "projection_transformations": [], "records": 1, "table": "client_escalations", "valid": true}`
- `{"file": "proof_events_latest.json", "missing_fields": [], "projection_transformations": [], "records": 2, "table": "proof_events", "valid": true}`
- `{"file": "connector_health_latest.json", "missing_fields": [], "projection_transformations": [], "records": 15, "table": "connector_health", "valid": true}`
- `{"file": "youtube_video_metadata_latest.json", "missing_fields": [], "projection_transformations": [], "records": 0, "table": "youtube_sources", "valid": true}`
- `{"file": "youtube_review_items_latest.json", "missing_fields": [], "projection_transformations": [], "records": 0, "table": "youtube_review_items", "valid": true}`
- `{"file": "social_drafts_latest.json", "missing_fields": [], "projection_transformations": ["tenant_id_defaulted_for_internal_export"], "records": 10, "table": "social_drafts", "valid": true}`
- `{"file": "subscription_membership_model_latest.json", "missing_fields": [], "projection_transformations": ["deterministic_id_derived", "tenant_id_defaulted_for_internal_export"], "records": 1, "table": "subscription_memberships", "valid": true}`
- `{"file": "payment_status_latest.json", "missing_fields": [], "projection_transformations": [], "records": 1, "table": "payments_status", "valid": true}`
