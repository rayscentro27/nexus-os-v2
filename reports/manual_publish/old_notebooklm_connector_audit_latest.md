# Old NotebookLM Connector Audit

Generated: 2026-06-29T18:34:53.959414+00:00

- ok: true
- status: legacy_adapter_found_cli_missing
- old_cli_found: false
- cli_path: None
- cli_version:
- files_found: 4
- wrote_directly_to_nexus: false
- legacy_dry_run_queue_supported: true
- consumer_browser_automation: false
- auth_attempted: false
- raw_secrets_included: false
- external_action_performed: false

## Files

- /Users/raymonddavis/nexuslive/scripts/check_notebooklm_cli.py
- /Users/raymonddavis/nexuslive/lib/notebooklm_ingest_adapter.py
- /Users/raymonddavis/nexuslive/scripts/test_notebooklm_ingest_adapter.py
- /Users/raymonddavis/nexuslive/docs/notebooklm_operator_workflow.md

## Recovery plan

- **selector_command:** nlm notebook list --json
- **source_commands:** ["nlm source list <notebook-id> --json", "nlm source get <source-id> --json"]
- **legacy_queue:** /Users/raymonddavis/nexuslive/reports/knowledge_intake/notebooklm_intake_queue.json
- **target_import_folders:** ["data/sources/notebooklm_exports", "data/sources/notebooklm_notes"]
- **apply_allowed:** False
- **review_required:** True
