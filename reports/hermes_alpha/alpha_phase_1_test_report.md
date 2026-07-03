# Hermes Alpha Phase 1 Test Report

## Focused command

`npx vitest run tests/hermes_alpha_no_supabase_guard.test.ts tests/hermes_alpha_brain_v1.test.ts tests/hermes_alpha_marketing_assets.test.ts tests/hermes_alpha_phase_1_harness.test.ts tests/hermes_alpha_research_adapter_v1.test.ts tests/hermes_alpha_workroom_ui_bridge.test.ts`

Result: **6 files passed, 36 tests passed**.

Coverage includes prohibited imports/connections, default-false flags, source order, offline business/trading/marketing behavior, 11 fixture evaluations, five prohibited-action refusals, adapter policy/routing/rejection, UI labels/separation/no execution control, draft-only bridge, and unchanged GoClear readiness response.

## Full command

`npm test`

Result: **39 files passed, 837 tests passed** in 18.28 seconds. No known unrelated failure remains.

Build/type verification also passed. Existing Vite esbuild/oxc deprecation notices and the existing large-bundle warning are non-blocking and unrelated to Alpha safety.
