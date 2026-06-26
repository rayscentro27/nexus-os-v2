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

`researching`, `summarized`, `scored`, `needs_review`, `approved`, `scheduled`, `implementing`, `done`, `parked`, `rejected`, `blocked`.

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
