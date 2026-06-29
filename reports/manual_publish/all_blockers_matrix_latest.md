# All Blockers Matrix

Generated: 2026-06-29T23:10:10.780463+00:00

- ok: true
- blockers: 17
- resolved_or_implemented: 4
- external_action_performed: false

## Matrix

- `{"blocker": "stripe_webhook", "cause": "Listener/triggers were untested", "fix_attempted": "Ran bounded signed test-mode listener and three triggers", "next_action": "Keep production/live mode disabled", "result": "bounded_test_listener_and_triggers_passed", "status": "resolved"}`
- `{"blocker": "stripe_checkout", "cause": "Browser completion required", "fix_attempted": "Generated local URL retrieval and test-card packet", "next_action": "Approve manual test Checkout completion", "result": "test_checkout_session_reused_open_not_completed", "status": "human_approval_required"}`
- `{"blocker": "stripe_payment_intent", "cause": "Test payment method confirmation not approved", "fix_attempted": "Generated pm_card_visa confirmation template", "next_action": "Approve test-method confirmation", "result": "requires_payment_method", "status": "human_approval_required"}`
- `{"blocker": "payment_onboarding", "cause": "No persistent writes allowed", "fix_attempted": "Mapped verified webhook events to dry-run records", "next_action": "Complete RLS/insert gates", "result": "webhook_events_mapped_to_onboarding_dry_run", "status": "dry_run_resolved"}`
- `{"blocker": "rls_direct", "cause": "Docker unavailable for remote dump", "fix_attempted": "Generated static proof and SQL Editor packet", "next_action": "Run read-only packet in Supabase SQL Editor", "result": "read_only_sql_packet_generated", "status": "human_dashboard_action_required"}`
- `{"blocker": "synthetic_rollback", "cause": "No guaranteed remote transaction channel", "fix_attempted": "Generated default-ROLLBACK insert/cleanup SQL packets", "next_action": "Run packets in SQL Editor and retain rollback proof", "result": "packets_ready_not_executed", "status": "human_dashboard_action_required"}`
- `{"blocker": "fake_customer_insert", "cause": "RLS/rollback proof incomplete", "fix_attempted": "Generated explicit insert and cleanup plans", "next_action": "Approve only after SQL Editor verification", "result": "blocked_gate_not_passed", "status": "blocked_by_safety_gate"}`
- `{"blocker": "frontend_live_data", "cause": "No live data row exists", "fix_attempted": "Implemented authenticated feature-flag path with fallback", "next_action": "Enable only after approved insert", "result": "live_read_path_implemented_flag_off", "status": "implementation_resolved_flag_off"}`
- `{"blocker": "resend_403", "cause": "403 plus sender-domain mismatch", "fix_attempted": "Diagnosed account/key permission and .cc/.com mismatch", "next_action": "Fix Resend key scope and verify goclearonline.com", "result": "resend_403_diagnosed_configuration_and_permission_blocker", "status": "human_account_fix_required"}`
- `{"blocker": "resend_email", "cause": "Sending prohibited", "fix_attempted": "Draft and approval card ready", "next_action": "Approve one test email only after 403 fix", "result": "draft_ready_not_sent", "status": "approval_required"}`
- `{"blocker": "youtube_transcript", "cause": "Approved TXT absent", "fix_attempted": "Created approved dropzone/template/import packet", "next_action": "Add approved/zbAmmnMh5ew.txt", "result": "dropzone_ready_waiting_for_approved_txt", "status": "human_source_required"}`
- `{"blocker": "notebooklm_sources", "cause": "No selected export present", "fix_attempted": "Recovered wrapper and created approved dropzone", "next_action": "Drop approved .txt/.md/.json export", "result": "dropzone_ready_waiting_for_export", "status": "human_source_required"}`
- `{"blocker": "oanda_demo", "cause": "Practice mode not explicit", "fix_attempted": "Blocked all network use and generated exact env fix", "next_action": "Set OANDA_ENVIRONMENT=practice and rerun", "result": "blocked_explicit_practice_environment_missing", "status": "env_configuration_required"}`
- `{"blocker": "vibe_cli", "cause": "CLI package absent/untrusted", "fix_attempted": "Created isolated install plan; legacy adapter works without it", "next_action": "Approve exact trusted package before install", "result": "vibe_cli_missing_legacy_backtest_available", "status": "optional_install_approval"}`
- `{"blocker": "vibe_backtest", "cause": "Recovered adapter had not run", "fix_attempted": "Ran deterministic synthetic backtest", "next_action": "Review results; keep broker disabled", "result": "synthetic_paper_backtest_passed", "status": "resolved"}`
- `{"blocker": "safe_schedule", "cause": "Permanent daemon not approved", "fix_attempted": "8/8 loop passed and launchd plan validated", "next_action": "Approve launchd install", "result": "launchd_plan_ready_not_installed", "status": "approval_required"}`
- `{"blocker": "real_onboarding", "cause": "No approved persistent test row/live read/payment completion", "fix_attempted": "Implemented all gates and rollback packets", "next_action": "Complete RLS, insert, auth membership, and feature flag approvals", "result": "not_live", "status": "blocked_by_safety_gate"}`
