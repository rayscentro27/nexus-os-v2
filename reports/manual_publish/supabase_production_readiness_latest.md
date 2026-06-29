# Supabase Production Readiness

Generated: 2026-06-29T16:39:08.334840+00:00

- ok: true
- status: ready_for_migration_review
- existing_migration_count: 14
- supabase_ready_export_count: 74
- mapped_export_count: 24
- raw_env_values_included: false
- live_database_inspected: false
- live_insertion_performed: false
- can_activate_today: migration_and_dry_run_yes; live tables only after Ray approval
- next_approval_command: supabase db push --dry-run (after reviewing DRAFT_client_portal_core_tables.sql and renaming it to a timestamped migration)
- external_action_performed: false
- summary: Local schemas, exports, insertion order, and RLS requirements are ready for review; no database call was made.

## Mapped exports

- `{"file": "admin_review_queue_latest.json", "table": "admin_review_queue"}`
- `{"file": "approval_cards_latest.json", "table": "approval_cards"}`
- `{"file": "approved_client_guidance_latest.json", "table": "approved_client_guidance"}`
- `{"file": "business_opportunities_latest.json", "table": "business_opportunities"}`
- `{"file": "business_profile_readiness_scores_latest.json", "table": "readiness_scores"}`
- `{"file": "business_profile_requirements_latest.json", "table": "business_profile_requirements"}`
- `{"file": "client_documents_latest.json", "table": "client_documents"}`
- `{"file": "client_escalations_latest.json", "table": "client_escalations"}`
- `{"file": "client_profiles_latest.json", "table": "client_profiles"}`
- `{"file": "client_questions_latest.json", "table": "client_questions"}`
- `{"file": "client_tasks_latest.json", "table": "client_tasks"}`
- `{"file": "connector_health_latest.json", "table": "connector_health"}`
- `{"file": "credit_profile_readiness_scores_latest.json", "table": "readiness_scores"}`
- `{"file": "credit_repair_workflow_latest.json", "table": "credit_workflow_items"}`
- `{"file": "dispute_letter_drafts_latest.json", "table": "dispute_letter_drafts"}`
- `{"file": "dispute_workflow_test_latest.json", "table": "dispute_cases"}`
- `{"file": "funding_readiness_scores_latest.json", "table": "funding_readiness_scores"}`
- `{"file": "partner_offers_latest.json", "table": "partner_offers"}`
- `{"file": "payment_status_latest.json", "table": "payments_status"}`
- `{"file": "proof_events_latest.json", "table": "proof_events"}`
- `{"file": "social_drafts_latest.json", "table": "social_drafts"}`
- `{"file": "subscription_membership_model_latest.json", "table": "subscription_memberships"}`
- `{"file": "youtube_review_items_latest.json", "table": "youtube_review_items"}`
- `{"file": "youtube_video_metadata_latest.json", "table": "youtube_sources"}`

## Blockers

- Ray migration approval
- linked Supabase project confirmation
- tenant membership seed
- RLS policy tests
- private storage policy
- insert execution approval
