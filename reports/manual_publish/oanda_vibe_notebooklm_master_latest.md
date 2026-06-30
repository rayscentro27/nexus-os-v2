# Oanda Vibe NotebookLM Master

Generated: 2026-06-30T01:32:40.575905+00:00

- ok: true
- build_result: passed
- safety_result: passed_no_raw_credentials
- oanda_credentials_detected: true
- oanda_demo_endpoint_verified: true
- oanda_account_check_passed: true
- oanda_pricing_check_passed: true
- oanda_instruments_check_passed: true
- oanda_demo_smoke_trade_placed: true
- oanda_demo_smoke_trade_closed: true
- oanda_live_endpoint_used: false
- oanda_live_or_funded_trade: false
- vibe_cli_found: false
- vibe_recovered_adapter_usable: true
- vibe_oanda_demo_bridge: vibe_oanda_demo_bridge_ready
- vibe_oanda_demo_strategy_smoke: demo_smoke_placed_and_closed
- notebooklm_cli_found: false
- legacy_notebooklm_connector_found: true
- notebooklm_selected_access_mode: legacy_adapter
- notebooks_listed: false
- notebooks_found_count: 0
- selected_notebooks_count: 0
- notebook_sync_status: watched_folder_sync_complete_no_selected_notebooks
- manual_export_still_required: true
- schedule_status: connector_schedules_registered_not_installed
- cli_registry_updated: true
- tool_access_violations: 0
- research_engine_updated: true
- frontend_status_updated: true
- ray_review_cards_created: 6
- hermes_recommendations_created: 7
- real_money_actions: false
- external_actions_performed: true
- exact_next_command: python3 scripts/activation/sync_selected_notebooklm_notebooks.py --json

## External actions

- Oanda practice account summary read
- Oanda practice instruments read
- Oanda practice AUD_USD pricing read
- Oanda one-unit demo smoke order and immediate close
- Vibe bridge one-unit Oanda demo strategy smoke and immediate close

## Remaining blockers

- Historical unofficial nlm CLI binary is missing, so live notebook listing is unavailable
- No NotebookLM export is present, so selected notebook count is zero
- Permanent connector schedules remain approval-gated
- Recurring demo strategy execution remains approval-gated
