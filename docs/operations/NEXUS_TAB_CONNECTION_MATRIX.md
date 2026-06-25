# Nexus OS v2 — Tab Connection Matrix (canonical)

Source of truth in code: `src/config/nexusTabs.ts` (this doc mirrors it for review). Drives the
sidebar badges + per-tab "Connection Status" panel + the Command Center "Systems Status" overview.

Status legend: **Live** = real v2 tables/scripts working · **Partial** = some live, some not ·
**Manual** = approved CLI, no UI submit yet · **Legacy** = useful v1 worker exists, v2 doesn't
control it · **Seed** = table exists, no workflow/data · **Hidden/Coming Soon** = not real/too risky.

| Tab | Status | Tables | Scripts | v1 dependency | Action capability | Gates | Next step |
|---|---|---|---|---|---|---|---|
| Command Center | Partial | approvals, agent_jobs, ops_incidents, creative_campaigns, nexus_events | — | — | chat, propose task_request, open tab | Hermes firewall | overview of all tabs |
| System Health | Live | system_health | nexus:watch | — | read | — | none |
| Agent Jobs | Live | agent_jobs, agent_registry | nexus_runner.py | — | view, queue dry-run | allowlist | none |
| Approvals | Live | approvals, social_posts | — | — | approve/reject/revise | admin RLS; sign-off only | none |
| GoClear / Apex | Partial | partner_offers, client_recommendations, monetization_opportunities | nexus:watch | — | view | no-guarantee compliance | seed offers + $97 intake backend |
| Opportunity Lab | Partial | monetization_opportunities | — | monetization-research | view | — | mirror v1 output into v2 |
| Source Intake & Review | Manual | research_sources, intake_events, transcript_reviews, dispositions | run_existing_youtube_monitor.py | research-engine collector | view; CLI capture (approved) | approved-only, dry-run default | run 1 approved capture → add URL UI |
| Creative Studio | Live | creative_campaigns/briefs/assets/scores, publish_readiness_packages | nexus:watch | content_employee | view, review packages | publishing gated | none |
| Design Library | Live | design_inspiration_sources, pattern_registry, feature_design_packets, ui_quality_reviews | — | — | browse | — | none |
| Trading Lab | Demo/Legacy | trading_strategy_candidates, trading_risk_rules | — | **trading_engine, auto_executor (trade-capable), tournament** | read-only display | **no live trading in UI** | show v1 status read-only |
| SEO / Marketing | Seed | seo_sites, seo_opportunities | — | — | view (empty) | — | seed tables |
| Model Router (AI Router) | Live | model_providers, model_routes, agent_registry | model_router.py | — | view | — | none |
| Integrations | Partial | model_providers | nexus:watch | cloudflared, hermes gateway | status-only (names) | never expose keys | env presence by name |
| Ops & Improvements | Live | ops_incidents, improvement_candidates, nexus_events | nexus:watch | ops scheduler, cron workers | view incidents + legacy fleet | read-only fleet | surface v1 fleet status |
| Events Feed | Live | nexus_events | — | — | read | — | none |
| Memory / Knowledge | Coming Soon (hidden) | nexus_lessons | — | memory_worker (cron) | — | — | add tab once seeded |

## Hermes Report Reader / Task Request
These are **modes inside Command Center**, not separate tabs. Report Reader = read-only safe report
interpretation; Task Request = create approval-gated task_requests. Both governed by the Hermes
firewall (public + internal_summary only).

## Failing v1 jobs (documented, NOT fixed here)
- `continuous-ops-daily` — launchd last exit **1**.
- `cf.hermes.gateway` — launchd last exit **11**.

## Action-capable v1 workers — never expose raw control in the v2 UI
`auto_executor.py`, `nexus_trading_engine.py`, social publishing, email send, scheduler load/unload,
`mac-mini-worker` exec. (Shown as observed status only.)
