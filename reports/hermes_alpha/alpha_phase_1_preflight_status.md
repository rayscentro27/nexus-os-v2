# Hermes Alpha Phase 1 Preflight Status

Date: 2026-07-03

## Git checkpoint

- Repository: `~/nexus-os-v2`
- Branch: `main`
- Latest commit: `756f199 plan and scaffold hermes alpha four phase architecture`
- Upstream: `origin/main`
- Working tree: not clean. Nine pre-existing cache/runtime report files are modified; none are Alpha source files and none will be included in this task.

## Isolation result

**PASS — implementation may continue.**

- Alpha is separate from Nexus Hermes under `src/hermes/alpha/`.
- No Alpha file imports or initializes a Supabase client.
- No Alpha file uses Supabase URLs, service-role credentials, client tables, or Nexus operational tables as authority.
- No Alpha file imports Oanda code, references practice/live endpoints, or contains order execution.
- No Research Vault adapter or connection exists.
- The provider router is mock-only and performs no fetch, HTTP, SDK, or external model call.
- No executable email sending, social publishing, payment charging, trade placement, production write, scheduler, or client-data access exists.
- Future provider/connection names occur only in disabled types/default-false flags and planning language.

## What exists

- Eight-node graph-style Alpha brain and six lanes.
- Deterministic opportunity, marketing, affiliate, trading, and general scoring.
- Process-local mock memory.
- Mock provider result with zero cost and no external call.
- Metadata-only research file adapter with allowed-root filtering.
- Draft-only Ray Review proposal format.
- Static no-Supabase/no-Oanda tests and architecture/design reports.

## What is still design or scaffold only

- No Alpha UI is mounted.
- No evaluation fixture runner or generated evaluation artifacts exist.
- Research adapter does not discover/read/validate real files; it validates supplied metadata only.
- Marketing output is a short placeholder rather than distinct landing/newsletter/social/image formats.
- Trading output describes research requirements but does not generate separate backtest and risk-review packets.
- No bridge writes to Ray Review or Nexus; this is intentional.
- Ollama, web research, Research Vault, Oanda, publishing, sending, charging, and production persistence remain disconnected.

## Recommended safe next actions

1. Add deterministic local fixtures and a pure evaluation runner.
2. Expand draft generators and trading research packets without adding side effects.
3. Mount a visibly offline/draft-only Alpha Workroom using static local evaluation/report data.
4. Extend the file adapter with bounded local discovery and validation against dedicated fixture/approved roots only.
5. Add explicit prohibited-action refusals and static/UI/adapter/bridge tests.
6. Keep all future connection flags false and all production actions unavailable.
