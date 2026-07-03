# Hermes Alpha No-Supabase Guard Result

Status: **passed**.

Static guard scope: `src/hermes/alpha/*.ts`.

- No Supabase package imports.
- No client creation calls.
- No client table names.
- No Nexus operational queue tables used as source authority.
- No Supabase URL/service-role environment variables.
- No Oanda practice/live endpoint or order calls.
- Future allow flags exist only in `alphaSafety.ts` and default false.
- Source order contains no database/Supabase entry.
- Brain responses set `noSupabaseUsed: true`.
- Mock provider performs no external call and reports zero cost.

Command: `npx vitest run tests/hermes_alpha_no_supabase_guard.test.ts tests/hermes_alpha_brain_v1.test.ts tests/hermes_alpha_marketing_assets.test.ts`

Current focused result: 7 Alpha files passed, 40 tests passed. TypeScript typecheck passed. Production build passed. Full suite passed: 40 files, 841 tests. The scan also rejects Research Vault connectors and external network/model invocation patterns. Inbox policy tests confirm empty approved folders are valid and README/placeholder files are not artifacts. This guard proves code shape and defaults; it is not permission to activate any future adapter.
