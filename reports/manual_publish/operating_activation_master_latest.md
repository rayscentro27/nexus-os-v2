# Operating Activation Master

Generated: 2026-06-30T02:25:07.818933+00:00

- ok: true
- build_result: passed
- safety_result: passed_no_raw_secrets
- scheduler_installed: true
- scheduler_type: launchd
- safe_jobs_scheduled: 27
- approval_gated_jobs: 7
- daily_operating_cycle: daily_operating_cycle_complete
- evening_closeout: evening_closeout_complete
- today_activation_score: 80
- hermes_advisor_inbox: hermes_advisor_inbox_ready
- ray_review_queue: ray_review_queue_refreshed
- client_message_draft_count: 11
- approval_receipts: approval_receipt_ledger_ready
- offer_registry: offer_registry_active
- revenue_dashboard: revenue_dashboard_active_internal
- lead_reactivation_draft_count: 5
- stripe_product_registry: stripe_test_product_registry_ready
- fake_customer_insert_status: not_inserted_approval_gated
- client_dashboard_live_read: live_read_test_blocked_fake_customer_or_flag_missing
- payment_to_onboarding: test_payment_onboarding_path_ready_external_steps_gated
- research_to_money: research_to_money_pipeline_active
- research_to_client: research_to_client_pipeline_ready
- research_to_content: research_to_content_pipeline_ready
- research_to_automation: research_to_automation_pipeline_ready
- content_calendar: seven_day_content_calendar_ready
- social_drafts: 5
- newsletter: newsletter_draft_ready_not_sent
- short_video_scripts: 5
- landing_page_experiments: 3
- lead_magnet: lead_magnet_outline_ready
- trading_demo_tournament: synthetic_demo_tournament_complete
- oanda_demo_reads: demo_account_check_passed
- vibe_oanda_bridge: vibe_oanda_demo_bridge_dry_run_passed
- notebooklm_watched_export: blocked_by_missing_source
- external_actions_performed: true
- real_charge: false
- email_sent: false
- sms_sent: false
- social_posts_published: false
- disputes_sent: false
- live_trades: false
- demo_trades_this_run: false
- ray_review_cards_created: 64
- hermes_recommendations_created: 12
- safe_to_leave_running: Two launchd calendar agents are loaded with KeepAlive=false; they run bounded internal/read-only/draft cycles and exit.
- exact_next_command: python3 scripts/activation/run_daily_operating_cycle.py --json

## External actions

- Installed two internal-safe launchd schedules
- Read-only Supabase fake-customer verification
- Oanda practice account/pricing/instrument reads
- YouTube metadata cache-aware refresh
- Resend read-only connection audit

## Remaining blockers

- Resend 403 configuration
- synthetic customer not inserted
- client live flag off
- Stripe test Checkout unpaid
- NotebookLM approved export missing
- external sends/publishing and recurring demo orders gated
