# Hermes Brain Golden Prompt Results

Implemented suite: `tests/hermes_master_contracts.test.ts` + `tests/hermes_production_polish.test.ts`

## Coverage

All required exact prompts are exercised, including the four-turn advisory transcript. Assertions cover route/handler identity, required response markers, banned policy/fallback phrases, source behavior, model/Supabase restrictions, selection-versus-advisory memory, draft-only actions, tenant/session isolation, partial Supabase verification, and clear-chat reset.

Additional regression cases cover:

- `pricing model for the offer` and `business model for GoClear` not entering AI-model status.
- One successful and one failed approvals table read producing `partial verification`.
- Session B not seeing Session A's selection or advisory context.
- Clear chat removing selection eligibility.

### Production Polish Coverage (29 additional tests)

- Casual/common conversation expansion: 6 exact prompts + 3 variants
- Specialist agent inventory: 3 exact prompts + 3 variants
- System health normalization: 6 variants
- Page/UI awareness: 4 exact prompts + 1 variant
- External/current info: 1 exact prompt
- Provenance/source wording: 2 tests
- Client record verification: 1 test
- Preserved behaviors: 2 tests

## Result

Targeted compatibility run after the route-contract implementation: 105/105 tests passed across the new suite and five high-risk legacy route suites.

Production polish run: 29/29 tests passed.

Final result: the complete repository suite passed 657/657 tests across 25 files. The production TypeScript/Vite build also passed.

## Before/After Summary

| Prompt Category | Before | After |
|----------------|--------|-------|
| Casual/common (6 prompts) | 6 fallback_clarification | 6 casual_common |
| Specialist inventory (3 prompts) | 3 local_reasoning | 3 specialist_agent_inventory |
| System health (6 variants) | 3 degraded, 3 process_inventory | 6 system_health_report |
| Page context (4 prompts) | 4 fallback_clarification | 4 page_context_status |
| External info (1 prompt) | 1 fallback_clarification | 1 external_current_info |
| Provenance labels | "local Nexus context" for casual | "common knowledge and local reasoning" |
| Client records | Contradictory "not verified" blocker | Honest "none for client_profiles read" |

## Remaining Limitations

- External info queries cannot provide real-time data (no live sports/news/weather feeds)
- Specialist agent registry is build-time; live agents require Supabase or config updates
- Page context requires UI to pass metadata; visual/DOM inspection not available from chat
