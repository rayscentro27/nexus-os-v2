# Nexus OS v2 — Tab Build Groups (priority order)

How to finish connecting the UI, grouped by readiness. Driven by `src/config/nexusTabs.ts`.

## Group A — Ready to connect now (real v2 tables/scripts)
- **Approvals** — Live (admin RLS fixed).
- **System Health** — Live (`system_health`).
- **Agent Jobs** — Live (`agent_jobs`, `agent_registry`).
- **Events Feed** — Live (`nexus_events`).
- **Creative Studio** — Live (creative tables).
- **Design Library** — Live (design tables).
- **Model Router / AI Router** — Live (`model_providers`, `model_routes`).
- **Command Center** — Partial→Live: now also the system-status overview.
- **Source Intake & Review** — Partial (data tables live; capture via CLI; UI submit pending).
- **Integrations** — Partial (status-only, names).

## Group B — Wrap v1 before connecting (useful Mac Mini workers exist)
- **YouTube / Research Monitor** — wrap `research-engine` collector to write **v2** tables (the
  wrapper exists; needs one approved capture). Do NOT double-run with v1 `youtube-channel-poller`.
- **Trading Lab** (backtest/tournament/demo) — show v1 trading worker **status read-only**; never
  execution.
- **Mac Mini Worker bridge** — show detected/running status; never raw control.
- **Research workers / legacy scheduler / Hermes gateway+tunnel** — read-only status surfacing.

## Group C — Needs seed/workflow before showing as primary (tables exist, empty)
- **SEO / Marketing** — seed `seo_sites` / `seo_opportunities`.
- **Opportunity Lab** — mirror v1 monetization-research into `monetization_opportunities`.
- **GoClear / Apex Revenue Hub** — seed offers + wire $97 intake/checkout backend.
- **Memory / Knowledge** — seed `nexus_lessons`, then add a tab.

## Group D — Hide or mark "Coming Soon" / Disabled (not real or too risky)
- **Live trading execution / raw `auto_executor` controls** — Hidden/Disabled (never in UI).
- **TikTok / Instagram real publishing** — Disabled (manual only).
- **Facebook real publish** — gated (one-post, approval + `publish_enabled`).
- **Public web search** — Disabled until a search provider is configured (`hermes-search` not deployed).
- **Any external integration with no test path** — Hidden until a safe test exists.

## Recommended build order
1. Group A polish (badges + Connection Status panels) — **done in this commit**.
2. Group B #1: run one approved YouTube capture into v2 tables (proves v1→v2 bridge).
3. Group B: read-only v1 fleet status in Ops & Trading tabs.
4. Group C: seed SEO/Opportunity/GoClear; mirror v1 monetization output.
5. Keep Group D hidden/gated.
