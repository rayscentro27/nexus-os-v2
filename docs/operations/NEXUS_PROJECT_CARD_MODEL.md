# Nexus Project Card Model

Department rooms use one project/work card shape defined in `src/config/nexusProjectTypes.ts` and mapped in `src/lib/nexusProjects.ts`.

## Fields

`project_id`, `title`, `department`, `owner_tab`, `project_type`, `status`, `score`, `score_label`, `priority`, `enrichment_status`, `enrichment_source`, `confidence`, `summary`, `pros`, `cons`, `recommendation`, `proposed_changes`, `proposed_schedule`, `next_action`, `hermes_memory_summary`, `category`, `destination`, `approval_required`, `feedback_requested`, `risk_triggers`, `visual_url`, `source_url`, `source_title`, `data_sources`, `related_process_id`, `related_task_request_id`, `related_approval_id`, `proof_event_id`, `enriched_at`, `reviewed_at`, `created_at`, `updated_at`.

## Canonical Enrichment Payload

The card model now recognizes `project_enrichment` from existing JSON fields. The payload includes `enrichment_status`, `summary`, `score`, `score_label`, `category`, `destination`, `pros`, `cons`, `recommendation`, `proposed_schedule`, `next_action`, `confidence`, `risk_triggers`, `approval_required`, `hermes_memory_summary`, `source_summary`, `enrichment_source`, `enriched_at`, `reviewed_at`, and `proof_event_id`.

Storage priority:

1. `transcript_reviews.metadata.project_enrichment`
2. `research_sources.metadata.project_enrichment`
3. `task_requests.payload.project_enrichment`
4. deterministic fallback from available row fields

## Feeder Output Shape

`NexusDepartmentFeederOutput` defines the standard intake shape for future feeders:

`feeder_id`, `department`, `project_type`, `title`, `summary`, `score`, `pros`, `cons`, `recommendation`, `proposed_schedule`, `next_action`, `source_url`, `source_title`, `data_sources`, `risk_triggers`, `approval_required`, `status`, `proof_event_type`, and `metadata`.

Feeder outputs should map into existing project card fields, `project_enrichment`, `task_requests.payload`, or metadata JSON. Schema changes should be avoided unless absolutely required.

## Statuses

`researching`, `summarized`, `scored`, `proposed`, `needs_review`, `approved`, `scheduled`, `implementing`, `done`, `parked`, `rejected`, `blocked`.

## Mappers

- `mapResearchSourceToProject`
- `mapCreativeAssetToProject`
- `mapTaskRequestToProject`
- `mapApprovalToProject`
- `mapProcessRegistryItemToProject`
- `mapSeoOpportunityToProject`
- `mapImprovementToProject`
- `mapOpportunityToProject`

## Helper Behavior

- `getProjectDepartment` returns the owning department.
- `getProjectReviewState` labels approval/review/block state.
- `getProjectScheduleLabel` explains schedule state without activating schedulers.
- `getProjectHermesRecommendation` gives Hermes a contextual recommendation and uses the pending-enrichment fallback when no summary exists.

No fake live data should be presented. If a department has no mapped rows, the UI says "No live projects yet" and names the feeder process/source.

## Opportunity Lab Feeder Cards

Opportunity Lab now also reads feeder-created `task_requests` where `task_type=opportunity_lab_project` or the payload marks `department=opportunity_lab`. These rows are created by `opportunity_lab_research_feeder` from existing enriched `research_sources`, and their payload maps directly to card fields:

- title and source reference from the related research source
- score, summary, pros, cons, recommendation, proposed schedule, and next action from `payload.project_enrichment`
- status from `task_requests.status`, including `proposed` and `needs_review`
- proof connection from the corresponding `nexus_events` row with `action=opportunity_lab_project_created`

## Department Feeder Cards

The project adapter now reads feeder-created `task_requests` for:

- Creative Studio: `creative_studio_project`
- Design Library: `design_library_project`
- SEO / Marketing: `seo_marketing_project`
- Agent Jobs: `agent_job_project`
- Command Center: `command_center_summary`
- Approvals: `approval_decision_project`
- Events Feed: `event_ledger_project`
- Integrations: `integration_status_project`
- Trading Lab: `trading_lab_research_project`, `trading_lab_backtest_import`

Each feeder card stores canonical card fields in `task_requests.payload` and `task_requests.payload.project_enrichment`, including title, department, owner tab, project type, score, summary, pros, cons, recommendation, proposed schedule, next action, risk triggers, approval requirement, source reference, and proof event id. Department workspaces and Command Center use the same adapter path, so counts update from real stored cards rather than fake data.

Trading Lab cards must also include `paper_only=true`, `live_trading_blocked=true`, `vibe_trading_status` or imported backtest status, and `risk_notes` in the payload/enrichment. Imported backtest cards store parsed metrics under `task_requests.payload.metrics` and deterministic recommendation fields under `task_requests.payload.project_enrichment`. Live broker execution is never represented as an available card action.
