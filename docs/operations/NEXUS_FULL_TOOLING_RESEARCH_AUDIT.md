# Nexus Full Tooling and Research Audit

Date: 2026-06-24

This is the durable operations version of the full audit. The matching report is:

`reports/manual_publish/nexus_full_tooling_research_audit_latest.md`

## Current State

Nexus OS v2 has a working core:

- React/Vite admin UI
- Supabase auth/RLS
- admin-gated table reads/writes
- approvals
- Hermes chat through Edge Function
- watch/report loop
- Nexus event proof ledger
- creative/approval/manual package scripts
- deterministic intake/research review scripts
- dry-run job runner

Nexus OS v2 is not yet a complete live operating system because the local/Mac command bridge, self-healing workflow, URL ingestion, and several integration surfaces are still disconnected or scaffolded.

## Connected Repos

- Main repo: `/Users/raymonddavis/nexus-os-v2`
- GitHub origin: `https://github.com/rayscentro27/nexus-os-v2.git`
- Branch: `main`
- Nested git dirs: none beyond root `.git`
- Netlify: GitHub-connected via `netlify.toml`

Local processes reference other Nexus-era repos/paths:

- `/Users/raymonddavis/nexus-ai`
- `/Users/raymonddavis/mac-mini-worker`
- Hermes Agent app/gateway

Those are running locally but are not governed by the nexus-os-v2 UI.

## Working Tools

- `npm run build`
- `npm run nexus:watch`
- `python3 scripts/nexus_runner.py --once --dry-run`
- `python3 scripts/intake/capture_intake_event.py`
- `python3 scripts/intake/review_transcript.py`
- `python3 scripts/intake/extract_service_opportunity.py`
- `python3 scripts/creative/generate_campaign_assets.py`
- `python3 scripts/creative/score_creative_assets.py`
- `python3 scripts/creative/create_creative_approvals.py`
- `python3 scripts/creative/create_publish_readiness_package.py --sample`
- `python3 scripts/social/facebook_token_status.py`
- `python3 scripts/model_router.py --self-test`
- `python3 scripts/hermes/request_model_route.py --agent hermes_advisor --prompt "..." --dry-run`

## Major Gaps

- No UI source submission form.
- No YouTube URL transcript fetcher.
- No article/website URL crawler.
- No Supabase Storage upload path for source files.
- No one-click safe runner from UI to Mac.
- No command registry table.
- No self-healing repair workflow.
- SEO and trading tabs are under-seeded.
- Integration registry is not the same as live connection status.

## Next Recommended Build

Build `Source Intake & Review` as the first operator-ready workflow:

1. Add paste/file/URL submission UI.
2. Save source into `intake_events`.
3. Queue or run deterministic transcript review.
4. Display review/disposition/opportunity results.
5. Let Hermes review the source and result safely.
