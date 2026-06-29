# Nexus Same-Day Operations Activation

Generated: 2026-06-29T16:42:16.545686+00:00

- ok: true
- status: operational_foundation_active
- nexus_live_working: true
- admin_working: true
- client_portal_working: true
- uncommitted_count_before_final_commit: 83
- youtube_before: queue_only_no_real_review
- youtube_after: targets_configured_connector_missing
- youtube_metadata_review: false
- youtube_transcript_review: false
- youtube_exact_setup: Add YOUTUBE_API_KEY locally/server-side or place one approved transcript .txt file in data/sources/youtube_transcripts/.
- social_connector_configured: true
- social_publish_blocked: true
- social_sandbox_step: Use a separately approved read-only Graph API /me/accounts request with token redaction.
- supabase_ready_for_table_creation: true
- migration_drafted: supabase/migrations/DRAFT_client_portal_core_tables.sql
- migration_table_count: 24
- insert_dry_run: dry_run_passed
- client_portal_paid_data_ready: false
- client_portal_mode: live_supabase_pending
- documents_messages_hardened: schema_hardened_storage_pending
- dispute_sandbox_plan_exists: true
- real_disputes_blocked: true
- payment_crm_path: configuration_found_approval_pending
- hermes_upgraded: true
- nexus_guide_upgraded: true
- ray_review_prioritized: true
- ray_approve_today_count: 12
- continuous_loop_running: true
- exact_next_command: python3 scripts/supabase/run_supabase_insert_dry_run.py --json
- exact_next_decision: Approve the 24-table Supabase draft/RLS local test plan and the $97 Stripe test-mode workflow; do not approve production execution yet.
- external_action_performed: false
- money_spent: false
- client_contacted: false
- public_content_published: false
- real_disputes_sent: false
- live_supabase_insertion: false

## Original env files

- /Users/raymonddavis/nexus-ai-council-sandbox/.env
- /Users/raymonddavis/nexus-os-v2/.env
- /Users/raymonddavis/nexuslive/.env

## Connector key names

- ALLOWED_TELEGRAM_USER_IDS
- LIVE_TRADING
- MAX_RESPONSE_CHARS
- META_APP_ID
- META_APP_SECRET
- META_INSTAGRAM_ACCOUNT_ID
- META_PAGE_ACCESS_TOKEN
- META_PAGE_ID
- MODEL_NAME
- NEXUS_DRY_RUN
- NEXUS_NETLIFY_PUBLIC_URL
- OANDA_ACCOUNT_ID
- OANDA_API_KEY
- OLLAMA_BASE_URL
- OPENROUTER_API_KEY
- PAPER_ONLY
- REQUEST_TIMEOUT_SECONDS
- RESEND_API_KEY
- RESEND_FROM_EMAIL
- RESEND_TO_EMAIL
- STRIPE_SECRET_KEY
- SUPABASE_SERVICE_ROLE_KEY
- SUPABASE_URL
- TELEGRAM_BOT_TOKEN
- TRADING_LIVE_EXECUTION_ENABLED
- VITE_ADMIN_EMAIL
- VITE_GEMINI_API_KEY
- VITE_HERMES_CHAT_ENABLED
- VITE_META_IG_ACCOUNT_ID
- VITE_META_PAGE_ACCESS_TOKEN
- VITE_META_PAGE_ID
- VITE_STRIPE_PRICE_ELITE
- VITE_STRIPE_PRICE_PRO
- VITE_STRIPE_PUBLISHABLE_KEY
- VITE_SUPABASE_ANON_KEY
- VITE_SUPABASE_URL
- VITE_TURNSTILE_SITE_KEY

## Blockers

- Ray migration approval
- linked Supabase project confirmation
- tenant membership seed
- RLS policy tests
- private storage policy
- insert execution approval

## Top 10

- `{"category": "backend/data", "effort": "large", "exact_next_action": "Review the draft migration, test tenant policies locally, and approve a timestamped migration.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": true, "helps_paid_client_onboarding": true, "impact": "backend/data", "priority": "P0 immediate", "rank": 1, "status": "needs_Ray_approval", "title": "Activate Supabase core tables and RLS", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
- `{"category": "client experience", "effort": "large", "exact_next_action": "Implement tenant membership and client profile reads after RLS passes.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": true, "helps_paid_client_onboarding": true, "impact": "client experience", "priority": "P0 immediate", "rank": 2, "status": "schedule", "title": "Replace demo client data with tenant-safe records", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
- `{"category": "automation", "effort": "small", "exact_next_action": "Add YOUTUBE_API_KEY server-side or one approved transcript file, then rerun intake.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": true, "helps_paid_client_onboarding": true, "impact": "automation", "priority": "P0 immediate", "rank": 3, "status": "needs_Ray_approval", "title": "Activate real YouTube metadata or transcript intake", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
- `{"category": "revenue", "effort": "medium", "exact_next_action": "Approve Stripe test mode, the $97 product/price, webhook mapping, and Supabase client creation.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": true, "helps_paid_client_onboarding": true, "impact": "revenue", "priority": "P0 immediate", "rank": 4, "status": "needs_Ray_approval", "title": "Approve the $97 payment and CRM path", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
- `{"category": "operations", "effort": "small", "exact_next_action": "Record approve/reject/defer for the same-day cards in priority order.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": true, "helps_paid_client_onboarding": true, "impact": "operations", "priority": "P0 immediate", "rank": 5, "status": "needs_Ray_approval", "title": "Process today's prioritized Ray Review queue", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
- `{"category": "safety/compliance", "effort": "large", "exact_next_action": "Create private bucket, retention rules, malware scanning, consent, and tenant/client RLS tests.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": true, "helps_paid_client_onboarding": true, "impact": "safety/compliance", "priority": "P0 immediate", "rank": 6, "status": "schedule", "title": "Build private document storage and message policies", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
- `{"category": "safety/compliance", "effort": "medium", "exact_next_action": "Approve non-deliverable sandbox recipients and proof-only vendor tests; keep production disabled.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": true, "helps_paid_client_onboarding": true, "impact": "safety/compliance", "priority": "P1 high", "rank": 7, "status": "needs_Ray_approval", "title": "Move dispute proof to synthetic sandbox testing", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
- `{"category": "automation", "effort": "small", "exact_next_action": "Approve a token-redacted /me/accounts identity check; do not post.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": false, "helps_paid_client_onboarding": true, "impact": "automation", "priority": "P1 high", "rank": 8, "status": "needs_Ray_approval", "title": "Validate the Meta connector read-only", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
- `{"category": "operations", "effort": "small", "exact_next_action": "Monitor nexus_today_ops heartbeat and stop it after eight cycles or earlier if needed.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": false, "helps_paid_client_onboarding": true, "impact": "operations", "priority": "P1 high", "rank": 9, "status": "do_now", "title": "Confirm the bounded continuous loop", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
- `{"category": "UI/UX", "effort": "medium", "exact_next_action": "Connect structured approved guidance and engine status after tenant-safe reads exist.", "files_systems_affected": ["client portal", "Supabase", "operations"], "helps_97_offer": true, "helps_monthly_subscription": true, "helps_paid_client_onboarding": true, "impact": "UI/UX", "priority": "P1 high", "rank": 10, "status": "schedule", "title": "Complete report-backed Hermes and Nexus Guide reads", "why_it_matters": "Closes a measured activation gap and moves Nexus toward safe paid-client automation."}`
