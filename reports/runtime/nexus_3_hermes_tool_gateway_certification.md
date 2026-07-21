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

The first deployed Edge Function smoke passed after repair:

- ordinary question `What is a pulley?`: `DIRECT_RESPONSE`, source `GENERAL_MODEL`, model `openai/gpt-4o-mini`
- Nexus question `How many clients do we have?`: `TOOL_REQUEST`, tool `get_client_aggregate`, tool executed, source `NEXUS_TOOL`
- targeted repair/reference sample: PASS after category-level repair guard
- targeted status/action sample after final patch: PASS for identity, date, schedule draft, task draft, Ray Review draft, provenance, client aggregate, Alpha/Supabase boundary, Stripe live status, trading status, and Engineering status

The 101-turn server holdout initially failed:

- result: 80/101
- score: 79.2%
- generic fallback count: 0
- duplicate actions: 0
- model calls: 129
- observed tokens: 193,216

The failures were concentrated in mandatory tool choice, provenance/reference handling, and explicit draft/tool routing. A follow-up category-level mandatory-tool policy was deployed after that holdout, but the full 101-turn holdout was not rerun to certification.

The following were not run in this environment:

- local browser against a locally served updated Edge Function,
- live Ray-only production acceptance,
- rollback verification in production.

Reason: the clean worktree has no Netlify auth token/site ID available, Netlify CLI status/deploy attempts hang without interactive auth, and production frontend deployment is blocked. The Edge Function is deployed; the production frontend is not.

## Certification State

`EDGE_DEPLOYED_TOOL_BRIDGE_NOT_FRONTEND_CERTIFIED`
