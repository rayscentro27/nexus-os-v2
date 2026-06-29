# Nexus Test Customer Connector Activation

Generated: 2026-06-29T18:40:30.978985+00:00

- ok: true
- status: test_connector_activation_complete
- test_customer_package_created: true
- package: $97 readiness review
- live_records_inserted: false
- stripe_cli_found: true
- stripe_test_mode_ready: true
- checkout_test_plan_ready: true
- payment_intent_test_plan_ready: true
- webhook_test_plan_ready: true
- payment_to_client_onboarding_ready: true
- real_charges_made: false
- old_notebooklm_cli_found: false
- old_notebooklm_adapter_found: true
- notebooklm_intake_ready: true
- notebooklm_sources_imported: 0
- youtube_api_active: true
- transcript_imported: 0
- youtube_mode: real_metadata_review_active_api
- oanda_demo_config_present: false
- oanda_mode: unverified
- vibe_trading_installed: false
- vibe_integration_status: legacy_paper_backtest_components_detected_vibe_cli_missing
- live_trades_placed: false
- payment_repo_concepts: 21
- ray_review_cards: 9
- automation_schedules: 22
- enabled_internal_automations: 18
- external_action_performed: false

## Blocked by env

- Stripe server-side test keys for application integration
- Stripe test webhook secret
- Explicit Oanda practice environment
- Approved YouTube transcript TXT

## Blocked by approval

- Approve Stripe CLI test Checkout
- Approve Stripe test PaymentIntent
- Approve Stripe webhook test
- Approve fake customer persistent Supabase insertion
- Approve NotebookLM CLI recovery integration
- Approve YouTube transcript import
- Approve Oanda demo + Vibe Trading paper/backtest integration test
- Approve payment repository roadmap
- Approve connector automation schedule activation

## Safe automations

- YouTube API cache refresh
- local transcript folder scan
- NotebookLM local import scan
- synthetic package generation
- payment plan generation
- connector audits
- static concept extraction
- Ray Review refresh
