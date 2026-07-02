# Hermes Brain Golden Prompt Results

Implemented suite: `tests/hermes_master_contracts.test.ts`

## Coverage

All required exact prompts are exercised, including the four-turn advisory transcript. Assertions cover route/handler identity, required response markers, banned policy/fallback phrases, source behavior, model/Supabase restrictions, selection-versus-advisory memory, draft-only actions, tenant/session isolation, partial Supabase verification, and clear-chat reset.

Additional regression cases cover:

- `pricing model for the offer` and `business model for GoClear` not entering AI-model status.
- One successful and one failed approvals table read producing `partial verification`.
- Session B not seeing Session A's selection or advisory context.
- Clear chat removing selection eligibility.

## Result

Targeted compatibility run after the route-contract implementation: 105/105 tests passed across the new suite and five high-risk legacy route suites.

Final result: the complete repository suite passed 628/628 tests across 24 files. The production TypeScript/Vite build also passed.
