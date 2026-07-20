# Nexus 3 Hermes Tool Gateway Certification

Generated: 2026-07-20

## Scope

This report covers the local implementation of the Hermes model-first governed tool bridge on branch `wave/hermes-model-first-language`.

## Implemented

- structured turn decision contract,
- central model-facing tool registry,
- OpenRouter decision stage,
- Capability OS-style validation gate,
- one server-side tool execution per approved request,
- OpenRouter grounded final-answer stage after tool output,
- sanitized trace metadata,
- tool-free direct response path,
- draft-only task / Ray Review / schedule tools,
- unknown-tool denial,
- malformed-argument denial,
- self-approval denial,
- aggregate-only client adapter,
- sanitized report list and summary adapter.

## Registered Tools

1. `get_current_time`
2. `get_hermes_identity`
3. `get_nexus_version`
4. `get_project_status`
5. `get_system_health`
6. `list_reports`
7. `summarize_report`
8. `get_client_aggregate`
9. `get_approval_summary`
10. `get_department_status`
11. `get_revenue_status`
12. `get_repo_intelligence_status`
13. `get_answer_provenance`
14. `draft_task`
15. `draft_ray_review`
16. `draft_schedule`

## Local Tests

- `npm test -- --run tests/hermes_existing_openrouter_model_first.test.ts tests/hermes_model_first_tool_bridge_contract.test.ts`: PASS, 8/8
- `npm run typecheck`: PASS
- `npm run build`: PASS with existing chunk-size warning
- `npm test -- --run`: PASS, 98 files / 1502 tests

## Generated Noise

Four readiness-report files contain timestamp-only generated diffs. They are classified as generated noise and are not part of this certification evidence.

## Not Yet Certified

The following were not run in this environment:

- local browser against a locally served updated Edge Function,
- 100-turn real OpenRouter holdout through the deployed tool bridge,
- live Ray-only production acceptance,
- rollback verification in production.

Reason: the clean worktree has no local Supabase/OpenRouter credentials, and the updated Edge Function is not deployed from this branch yet.

## Certification State

`LOCAL_TOOL_BRIDGE_PASS_NOT_LIVE_DEPLOYED`
