# Nexus Project Card Model

Department rooms use one project/work card shape defined in `src/config/nexusProjectTypes.ts` and mapped in `src/lib/nexusProjects.ts`.

## Fields

`project_id`, `title`, `department`, `owner_tab`, `project_type`, `status`, `score`, `priority`, `summary`, `pros`, `cons`, `recommendation`, `proposed_changes`, `proposed_schedule`, `next_action`, `approval_required`, `feedback_requested`, `risk_triggers`, `visual_url`, `source_url`, `source_title`, `data_sources`, `related_process_id`, `related_task_request_id`, `related_approval_id`, `proof_event_id`, `created_at`, `updated_at`.

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
