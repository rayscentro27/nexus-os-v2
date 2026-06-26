# Nexus Department Automation Feeders

## Verification Summary

- Department feeder model added in `src/config/nexusDepartmentFeeders.ts`.
- Manual feeder runner added at `scripts/automation/run_department_feeder.py`.
- Department rooms show feeder status and next action.
- Command Center shows feeder state counts and top feeder recommendation.
- `npm run build` passed.
- `npm run nexus:watch` passed in manual mode.
- Feeder dry-run passed and wrote only local reports.
- No scheduler, capture, yt-dlp, external AI, publish, send, trade, deploy, social publish job, or v1 worker path was run.

- generated_at: 2026-06-26T02:30:56.113337+00:00
- mode: DRY-RUN (no Supabase writes)
- feeders: 5 · no_external_ai: true
- scheduler_started: false · capture_run: false · publish/send/trade/deploy: false

## Results
- {"candidates": ["research_sources"], "department": "source_intake", "dry_run": true, "enabled_state": "manual_only", "feeder_id": "source_intake_enrichment_backfill", "manual_command": "python3 scripts/intake/backfill_project_enrichment.py --dry-run --limit 10 --no-external-ai", "name": "Source Intake Enrichment Backfill", "next_action": "Run dry-run, then bounded metadata-only live backfill when safe.", "proof_event_type": "project_enrichment_backfilled", "risk_level": "low", "status": "dry_run_reported", "target_tables": ["research_sources.metadata", "transcript_reviews.metadata", "nexus_events"], "would_write": []}
- {"candidates": ["task_requests"], "department": "source_intake", "dry_run": true, "enabled_state": "manual_only", "feeder_id": "source_capture_queue_worker", "manual_command": "python3 scripts/intake/run_capture_queue_worker.py --once --limit 1 --dry-run --no-external-ai", "name": "Source Capture Queue Worker", "next_action": "Keep dry-run default; live run only for safe queued items.", "proof_event_type": "source_enriched_for_project_card", "risk_level": "medium", "status": "dry_run_reported", "target_tables": ["task_requests", "research_sources", "intake_events", "transcript_reviews", "nexus_events"], "would_write": []}
- {"candidates": ["reports/manual_publish/nexus_active_automation_audit_latest.md", "reports/manual_publish/nexus_approval_preview_and_hermes_review_latest.md", "reports/manual_publish/nexus_capture_queue_worker_latest.md", "reports/manual_publish/nexus_command_center_and_source_intake_polish_latest.md", "reports/manual_publish/nexus_department_automation_feeders_latest.md"], "department": "ops_improvements", "dry_run": true, "enabled_state": "manual_only", "feeder_id": "ops_improvement_research_feeder", "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id ops_improvement_research_feeder --dry-run --limit 5 --no-external-ai", "name": "Ops Improvement Research Feeder", "next_action": "Dry-run candidate creation from existing safe reports; live writes deferred.", "proof_event_type": "department_feeder_ops_improvement_reported", "risk_level": "low", "status": "dry_run_reported", "target_tables": ["task_requests", "nexus_events"], "would_write": []}
- {"candidates": ["research_sources with project_enrichment destination Opportunity Lab/GoClear/Apex"], "department": "opportunity_lab", "dry_run": true, "enabled_state": "manual_only", "feeder_id": "opportunity_lab_research_feeder", "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --dry-run --limit 5 --no-external-ai", "name": "Opportunity Lab Research Feeder", "next_action": "Dry-run promotion candidates; live creation can be added after review.", "proof_event_type": "department_feeder_opportunity_reported", "risk_level": "low", "status": "dry_run_reported", "target_tables": ["task_requests", "nexus_events"], "would_write": []}
- {"candidates": ["creative_assets", "social_posts", "publish_readiness_packages"], "department": "creative_studio", "dry_run": true, "enabled_state": "manual_only", "feeder_id": "creative_design_project_feeder", "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id creative_design_project_feeder --dry-run --limit 5 --no-external-ai", "name": "Creative and Design Project Feeder", "next_action": "Dry-run candidate mapping; publish remains approval-gated.", "proof_event_type": "department_feeder_creative_design_reported", "risk_level": "medium", "status": "dry_run_reported", "target_tables": ["task_requests", "creative_assets.metadata", "nexus_events"], "would_write": []}
