# Nexus OS v2 — Tab Connection Plan (report)

- generated_at: 2026-06-25 · build PASS · watch PASS
- canonical config: `src/config/nexusTabs.ts`
- docs: `NEXUS_TAB_CONNECTION_MATRIX.md`, `NEXUS_TAB_BEHAVIOR_RULES.md`, `NEXUS_TAB_BUILD_GROUPS.md`

## What changed in the UI (smallest safe change)
- New `src/config/nexusTabs.ts` — canonical per-tab status model + detected v1 fleet list.
- New `src/components/TabStatus.tsx` — `StatusBadge`, `TabConnectionStatus` panel, `SystemStatusOverview`.
- `src/components/Shell.tsx` — sidebar status **badges** per tab; a **Connection Status** panel at the
  top of every tab; a **Systems Status overview** on Command Center. Routing unchanged; no `sections.tsx`
  edits (lower risk). No new actions, no v1 control.

## Tab status snapshot
- **Live:** System Health, Agent Jobs, Approvals, Creative Studio, Design Library, Model Router, Events Feed.
- **Partial / Manual:** Command Center (Partial), GoClear/Apex (Partial), Opportunity Lab (Partial),
  Integrations (Partial, status-only), **Source Intake & Review (Manual/CLI)**.
- **Legacy / Demo (v1 not wrapped):** Trading Lab (read-only display; trading workers are v1).
- **Seed required:** SEO / Marketing (empty tables).
- **Hidden/Coming Soon:** Memory/Knowledge.

## Tabs depending on v1 legacy processes
- Source Intake / YouTube Monitor → `research-engine` (yt-dlp) + `youtube-channel-poller`.
- Trading Lab → `nexus_trading_engine.py`, `auto_executor.py`, `tournament_service.py`.
- Ops → `operations_center/scheduler.py` + cron workers.
- Integrations/Command Center → hermes gateway + cloudflared tunnels + `mac-mini-worker`.

## Tabs to hide / disable
Live trading execution, raw `auto_executor` controls, TikTok/Instagram real publish, public web
search (provider not configured), any untested external integration. (FB real publish stays gated.)

## v1 processes to wrap first
YouTube/research capture → write **v2** tables (Group B #1). Then mirror v1 monetization-research
into `monetization_opportunities`, and add read-only v1 fleet status to Ops/Trading.

## Failing v1 jobs (documented, not fixed)
- `continuous-ops-daily` exit 1 · `cf.hermes.gateway` exit 11. Surfaced in the Command Center overview.

## Command Center now summarizes
Live / Partial / Legacy / Seed tab groups, detected v1 fleet count, failing legacy jobs, and the
action-capable v1 workers that must never be raw-exposed. Buttons only open the related tab.

## Safety
No publish/send/trade/deploy; no scheduler started/stopped; no process killed; no real capture; no
secrets; `.env` not committed; v1 untouched; approval `13eafcab` pending; FB `publish_enabled` false.

## Next build recommendation
Group B #1 — run ONE approved YouTube capture into v2 tables (needs a Ray-approved public URL), then
surface read-only v1 fleet status in the Ops tab.
