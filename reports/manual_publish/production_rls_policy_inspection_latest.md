# Production RLS Policy Inspection

Generated: 2026-06-29T20:17:50.467369+00:00

- ok: false
- status: remote_rls_inspection_blocked_docker_static_migration_verified
- linked_project: iqjwgpnujbeoyaeuwehj
- schema_dump_temporary_deleted: true
- static_rls_definitions_count: 25
- policies_detected_count: 0
- direct_remote_verification_blocker: Remote schema dump requires Docker with this Supabase CLI version. Applied migration and static RLS definitions are present, but direct production policy verification is incomplete.
- tenant_isolation_required: true
- rls_disabled: false
- database_write_performed: false
- raw_secrets_included: false
- external_action_performed: false

## Verified RLS tables


## Missing

- admin_review_queue
- approval_cards
- approved_client_guidance
- business_opportunities
- business_profile_requirements
- client_documents
- client_escalations
- client_profiles
- client_questions
- client_tasks
- connector_health
- credit_workflow_items
- dispute_cases
- dispute_letter_drafts
- engine_runs
- funding_readiness_scores
- partner_offers
- payments_status
- proof_events
- readiness_scores
- social_drafts
- subscription_memberships
- tenant_memberships
- youtube_review_items
- youtube_sources
