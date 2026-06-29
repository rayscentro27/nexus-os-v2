# Supabase DB Push Gate

Generated: 2026-06-29T16:58:51.702357+00:00

- ok: true
- attempted: false
- dry_run_attempted: true
- result: skipped_by_gate
- target_project: iqjwgpnujbeoyaeuwehj
- target_verified: true
- linked_project_name: nexus-os-v2
- blocker: Remote history lacks 0012_client_workflow_engine.sql; db push dry-run demands --include-all. Local execution testing is also unavailable.
- include_all_used: false
- db_reset_used: false
- destructive_operation_performed: false
- next_fix: Review/test migration 0012 and the timestamped portal migration locally, then reconcile migration history before a new approved push.
- external_action_performed: false
