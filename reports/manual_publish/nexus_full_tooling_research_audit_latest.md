# Nexus OS v2 Full Tooling, Repo, Process, and Research Engine Audit

Date: 2026-06-24

## Executive Truth Map

Nexus OS v2 is a real Supabase-backed operating dashboard with working auth, RLS, approvals, event proof, Hermes chat, reports, creative packages, and bounded local scripts. It is not yet a fully operator-ready OS because several tabs show raw tables instead of workflows, and the Mac/local execution bridge is not connected end-to-end from the UI/Hermes to allowlisted command execution.

The research engine is partially ready: pasted text, local transcript files, and manual ideas can be captured and processed by deterministic scripts into reviews, dispositions, opportunities, lessons, and improvement candidates. It does not yet ingest YouTube URLs, article URLs, website URLs, uploaded files through the UI, or NotebookLM exports automatically.

## Repo and GitHub

| Item | Status |
|---|---|
| Main repo | `/Users/raymonddavis/nexus-os-v2` |
| Branch | `main` |
| Origin | `https://github.com/rayscentro27/nexus-os-v2.git` |
| Latest commit at inspection | `741a398 add approval previews and hermes review` |
| Worktree | clean at start |
| Ahead/behind at start | `0/0` |
| Nested git dirs | only `./.git` |
| Netlify | GitHub-connected by `netlify.toml`; push to `main` should build `npm run build` and publish `dist` |
| Supabase project ref | linked metadata shows `iqjwgpnujbeoyaeuwehj` |

External/local repo references found in process state and docs: `~/nexus-ai`, `~/mac-mini-worker`, Hermes Agent, local Nexus trading/research workers, and legacy launchd services. They are running locally but are not cleanly governed by nexus-os-v2 UI.

## npm / Frontend Tools

| Script | Command | Purpose | Safe now | Reads Supabase | Writes Supabase | Writes reports | Can publish/send/trade/deploy | Status |
|---|---|---|---|---|---|---|---|---|
| `dev` | `vite` | local frontend dev server | yes | browser reads when used | browser writes through UI buttons | no | no | working manually |
| `build` | `tsc --noEmit && vite build` | typecheck/build | yes | no | no | writes `dist` | no | working |
| `preview` | `vite preview` | preview built app | yes | browser reads when used | browser writes through UI buttons | no | no | available |
| `typecheck` | `tsc --noEmit` | TS validation | yes | no | no | no | no | available |
| `seed:day1` | `python3 scripts/seed_day1_event.py` | seed initial ledger/health/approval | with constraints | yes | yes | no | no | working but writes DB |
| `nexus:watch` | `python3 scripts/run_nexus_continuous_operations.py --mode manual` | bounded activation/status/report loop | yes | yes | yes | yes | no real publish/trade; email idempotent/already_sent | working |
| `nexus:overnight` | `python3 scripts/run_nexus_overnight_safe_ops.py` | bounded multi-cycle watch loop | with constraints | yes | yes | yes | no permanent scheduler | working manually, not started |

No automated test script is defined beyond typecheck/build.

## Python Scripts and Runners

| File | Purpose | Example command | Env/config names | Supabase | Reports | Action-capable | Status |
|---|---|---|---|---|---|---|---|
| `scripts/run_nexus_continuous_operations.py` | bounded watch/report loop | `npm run nexus:watch` | Supabase, Netlify, Resend, Meta, TikTok, Oanda, Oracle, OpenRouter names | read/write | yes | external checks only; idempotent email state | working |
| `scripts/run_nexus_overnight_safe_ops.py` | bounded overnight cycles | `npm run nexus:overnight -- --cycles 3` | Supabase | read/write | yes | no permanent scheduler | working manually |
| `scripts/nexus_runner.py` | allowlisted `agent_jobs` runner | `python3 scripts/nexus_runner.py --once --limit 1 --dry-run` | Supabase service env | read/write | no | can dry-run jobs; real publish requires extra gates | working manually |
| `scripts/run_social_publish_job.py` | one social publish job executor | `python3 scripts/run_social_publish_job.py --dry-run` | Supabase, Meta token names | read/write | no | real publish only with `--real-publish` and gates | dry-run safe, real unsafe until approved |
| `scripts/social/facebook_publisher.py` | Facebook adapter | called by runner | Meta token env, Supabase | read/write | no | real publish gated by approval + token + `publish_enabled` | working/gated |
| `scripts/social/facebook_token_status.py` | read-only token status | `python3 scripts/social/facebook_token_status.py` | `META_PAGE_ACCESS_TOKEN`, `META_APP_ID`, `META_APP_SECRET` | writes health/events | no | no | working when token present |
| `scripts/social/social_quality_check.py` | offline social QA | `python3 scripts/social/social_quality_check.py --post-id <id>` | Supabase | read/write | no | no | working |
| `scripts/intake/capture_intake_event.py` | capture pasted text/file intake | `python3 scripts/intake/capture_intake_event.py --title X --text Y` | Supabase | write | no | no | working manually |
| `scripts/intake/review_transcript.py` | deterministic transcript/idea classifier | `python3 scripts/intake/review_transcript.py --sample` | Supabase | read/write | no | no | working manually |
| `scripts/intake/extract_service_opportunity.py` | draft productized service opportunity | `python3 scripts/intake/extract_service_opportunity.py --sample` | Supabase | read/write | no | no | working manually |
| `scripts/compliance/classify_claim_risk.py` | local claim risk classifier | `python3 scripts/compliance/classify_claim_risk.py --text ...` | optional Supabase | optional event | no | no | working |
| `scripts/creative/generate_campaign_assets.py` | deterministic creative drafts | `python3 scripts/creative/generate_campaign_assets.py` | Supabase | write | no | no | working |
| `scripts/creative/score_creative_assets.py` | compliance/QA scoring | `python3 scripts/creative/score_creative_assets.py` | Supabase | read/write | no | no | working |
| `scripts/creative/create_creative_approvals.py` | create approval cards from scored assets | `python3 scripts/creative/create_creative_approvals.py` | Supabase | read/write | no | creates approvals only | working |
| `scripts/creative/create_social_post_drafts.py` | create draft social posts | `python3 scripts/creative/create_social_post_drafts.py` | Supabase | read/write | no | no publish | working |
| `scripts/creative/_publish.py` and wrappers | manual publish package/review/export/receipt | `python3 scripts/creative/create_publish_readiness_package.py --sample` | Supabase | read/write | exports packages | no real publish | working manually |
| `scripts/creative/_design.py` and design scripts | design variants, scoring, inspiration, UI reviews | `python3 scripts/design/review_ui_quality.py --title X` | Supabase | read/write | no | no | working manually |
| `scripts/model_router.py` | deterministic route decision | `python3 scripts/model_router.py --self-test` | Supabase for routes | read | no | no external model call | working |
| `scripts/hermes/request_model_route.py` | record Hermes model route dry run | `python3 scripts/hermes/request_model_route.py --agent hermes_advisor --prompt X --dry-run` | Supabase | read/write | no | no external call by default | working |
| `scripts/hermes/build_hermes_context.py` | safe Hermes context snapshot | `python3 scripts/hermes/build_hermes_context.py` | Supabase | read/write event | `/tmp` | no | working |
| `scripts/client_agents/client_answer_stub.py` | approved knowledge client answer stub | `python3 scripts/client_agents/client_answer_stub.py --question X` | Supabase | read/write event | no | no | scaffold/working stub |
| `scripts/seed_*.py` | idempotent seed/setup scripts | run individually | Supabase | write | no | no real external action | working but setup-only |

## Running Local Processes

Observed, not modified:

- nexus-os-v2 Vite/esbuild processes are running.
- Hermes Agent desktop/gateway processes are running.
- `~/nexus-ai` orchestrator, research worker, research signal bridge, trading engine, auto executor, scheduler, dashboard, control center, and tournament services are running.
- `~/mac-mini-worker/src/mac-mini-worker.js` is running.
- launchd contains many `com.nexus.*` jobs.
- `tmux ls` reported no tmux server.

These prove local infrastructure exists, but not that nexus-os-v2 controls it safely.

## Supabase / Database

Applied migrations match local through `20260624190000`.

Tables with rows: `nexus_events`, `agent_jobs`, `approvals`, `social_accounts`, `social_posts`, `social_publish_receipts`, `creative_assets`, `telegram_messages`, `system_health`, `admin_users`, `workspaces`, `agent_registry`, `monetization_opportunities`, `partner_offers`, `creative_campaigns`, `creative_briefs`, `creative_scores`, `studio_outputs`, `model_providers`, `model_routes`, `integration_registry`, `trading_risk_rules`, `worker_heartbeats`, `improvement_candidates`, `approved_knowledge`, `model_route_decisions`, `hermes_model_requests`, `intake_events`, `orientation_notes`, `transcript_reviews`, `dispositions`, `wagers`, `nexus_lessons`, design tables, publish package tables.

Empty or not yet materially used: `business_opportunities`, `trading_signals`, `demo_trades`, `research_runs`, `research_sources`, `opportunity_experiments`, `client_recommendations`, `model_usage_logs`, `trading_strategy_candidates`, `trading_backtests`, `seo_sites`, `seo_opportunities`, `ops_incidents`, `task_requests`.

Edge Functions:

- `hermes-chat`: working chat provider path through server-side provider keys; no secrets in browser.
- `hermes-search`: exists but should not be deployed/used unless explicitly approved and configured.
- `_shared/firewall.ts`: sensitivity firewall.

RLS:

- Admin read policies are now fixed through `public.nexus_is_active_admin()`.
- Frontend uses anon key only.
- Service role is used only by local scripts.

## Integrations

| Integration | Status | Purpose | Required names | Safe test |
|---|---|---|---|---|
| Supabase | connected/working | DB, auth, RLS, Edge Functions | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | `npm run nexus:watch`, UI reads |
| Netlify | connected by GitHub | live UI/static landing | CLI optional: `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID` | push main / inspect deploy |
| Resend | partially configured/working idempotent | one test email | `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, recipient env | watch reports `already_sent` |
| Meta Facebook | token tested, publish blocked | one gated page post | `META_PAGE_ACCESS_TOKEN`, `META_APP_ID`, `META_APP_SECRET` | `facebook_token_status.py`; no publish |
| Instagram | registered/manual | future social posting | `INSTAGRAM_BUSINESS_ACCOUNT_ID` etc. | none safe beyond package |
| TikTok | registered/manual | future video/social | `TIKTOK_ACCESS_TOKEN` etc. | none |
| Telegram | scaffold/guarded | War Room output proof | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | guarded dry-run only |
| Oanda Demo | connected/tested | demo/paper connection | `OANDA_*`, `PAPER_ONLY`, `NEXUS_DRY_RUN` | watch demo status |
| Oracle worker | reachable/read-only | remote worker/model host | `ORACLE_*` or SSH key | watch read-only status |
| YouTube transcripts | registered only | source intake | none in repo | no fetch script exists |
| NotebookLM manual | manual only | paste/export notes | none | capture pasted text/file |
| GSC/GA/DataForSEO | registered only | SEO engine | provider-specific keys | none |
| OpenRouter | connected for Hermes | chat/model route | `OPENROUTER_API_KEY`, Hermes model env | Hermes chat |
| Ollama/llama.cpp/NVIDIA NIM | registered/reference/local candidate | local/private model route | `OLLAMA_URL` etc. | route decision only |
| Gemini/Claude/ChatGPT/Codex manual | manual routes | model packets/manual agent work | none or external app auth | manual |
| SuperMemory/GraphRAG/MarkItDown | registered/reference | memory/research ingestion | provider-specific if used | no working integration |
| Wayland/Vibe Trading | reference only | research/reference | none | none |

## Research Engine Readiness

| Input Type | Supported now | Storage | Analyzer | Routes onward | UI form |
|---|---|---|---|---|---|
| Pasted transcript/text | yes, CLI | `intake_events.raw_text` | `review_transcript.py` | reviews, notes, dispositions, opportunities/improvements | no |
| Local transcript file | yes, CLI | `intake_events` or direct review | `review_transcript.py --file` | same | no |
| Manual idea | yes, CLI/job | `intake_events`, `transcript_reviews` | deterministic classifier | Opportunity/Ops/Creative candidates | no |
| NotebookLM export/summary | manual paste/file | same | deterministic review | same | no |
| YouTube URL | not fetched | can store source_url manually | no URL fetch/transcript extraction | no automatic route | no |
| YouTube transcript | supported if pasted/file | `intake_events` | yes | yes | no |
| Article/blog URL | not fetched | source_url only | no fetch/summarize | no | no |
| Website URL | not fetched | source_url only | no crawler | no | no |
| Uploaded file in UI | no | none | no | no | no |
| Research notes | yes as text/file | intake/review tables | yes | partial | no |

Research status: **partially ready, script/database-ready, not operator-ready**.

## UI Tab Audit

| Tab | Current classification | Recommendation |
|---|---|---|
| Command Center | keep primary | Add explicit tool command/status surface; clarify read-only vs task creation |
| System Health | keep but improve | Turn into System Doctor with causes, fixes, next actions |
| Agent Jobs | keep but improve | Replace red-dot table feel with job explanations, dry-run/real gates, next command |
| Approvals | keep primary | Preview/Hermes review now improved; next add linked package/media completeness badges |
| GoClear / Apex | rename/improve | Make Revenue Hub with offer stats, affiliate partners, leads, follow-ups |
| Opportunity Lab | keep but improve | Add score explanations, review workflow, submit-source path |
| Intake & Orientation | rename | Rename Source Intake & Review; add paste/upload/URL form |
| Creative Studio | keep but improve | Add visual campaign workflow and preview grid |
| Design Library | keep but improve | Keep as reference/design QA support surface |
| Trading Lab | keep but constrain | Research/demo only; show strategies, backtests, demo status, no live execution |
| SEO / Marketing | hide until seeded or rebuild | Build SEO Growth Engine before primary placement |
| Model Router | rename/improve | AI Router / Agent Console; show route policy and available models |
| Integrations | keep but improve | Show real connection/test status, not just registry |
| Ops & Improvements | keep but improve | Convert into action backlog with owner/status/next command |
| Events Feed | keep but improve | Add grouping, filters, “what changed” summaries |

## Mac / Local Execution Bridge

Current reality:

- Hermes in the browser can create `task_requests` after approval and can queue some `agent_jobs`.
- Nexus UI can create `agent_jobs` for creative and dry-run flows.
- `scripts/nexus_runner.py` can consume allowlisted `agent_jobs` manually.
- Handler allowlist exists in `scripts/runner_handlers/__init__.py`.
- Runner writes job results and `nexus_events`.
- Results are visible in Agent Jobs and Events Feed.

Missing:

- No one-click UI runner.
- No secure browser-to-Mac command bridge in nexus-os-v2.
- No daemon/scheduler intentionally enabled for this repo.
- No unified command registry table with approval requirements.
- Legacy `nexus-ai` and `mac-mini-worker` processes are running but not cleanly controlled by nexus-os-v2.

## Recommendations

1. Actually working today: Supabase auth/RLS/UI reads, approvals, Hermes chat, report reader, watch loop, creative drafting/scoring/approvals, manual publish packages, deterministic intake review, model routing decisions, dry-run runner, Facebook token checks, Oanda demo status, Oracle read-only checks.
2. Registered but not functional: GSC, GA, DataForSEO, TikTok, Instagram publishing, YouTube transcript fetch, MarkItDown, GraphRAG, SuperMemory, local model routes beyond references.
3. Mock/scaffolded: client answer stub, several job handlers, SEO Growth Engine, Trading Lab strategy/backtest surfaces, Mac bridge, self-healing doctor.
4. Tools Ray/Codex can safely run today: `npm run build`, `npm run nexus:watch`, `python3 scripts/nexus_runner.py --once --dry-run`, intake scripts with pasted text/files, creative scoring/package scripts, model router dry runs, Facebook token status.
5. Research engine readiness: partially ready; script/database-ready but not UI-ready and no URL/video fetch.
6. Missing for YouTube/transcripts: URL fetch/transcript extractor, source submission UI, file upload/storage, dedupe, queue, review status UI.
7. Missing for Hermes to command tools: explicit command registry, UI/Hermes command-to-job mapping, approvals for command execution, local runner bridge, result display.
8. Missing for self-healing: diagnostic rules, repair suggestions, safe repair approval flow, issue-to-job conversion.
9. Hide until connected: SEO/Marketing, external research integrations, live trading surfaces, public search if disabled, TikTok/Instagram publishing, GraphRAG/SuperMemory/MarkItDown.
10. Top 10 repair priorities:
    1. Build Source Intake UI for pasted text/file/URL.
    2. Add YouTube transcript ingestion using safe manual transcript or approved fetcher.
    3. Add Mac command registry + one safe `nexus_watch` bridge command.
    4. Convert Agent Jobs into operator workflow cards.
    5. Convert System Health into System Doctor.
    6. Add integration connection-test rows and UI status.
    7. Add Opportunity Lab review/approve/promote workflow.
    8. Add GoClear Revenue Hub metrics and lead/follow-up pipeline.
    9. Add SEO Growth Engine seed workflow before showing as primary.
    10. Add Trading Lab backtest/demo proof UI, keep live trading hidden.
11. Next one Codex change after approval: build the Source Intake & Review UI that captures pasted text/file/URL into `intake_events`, queues/executes deterministic review safely, and displays disposition/opportunity outputs.

## Safety Confirmation

This audit did not publish, send email, place trades, start schedulers, approve anything, set `publish_enabled=true`, deploy manually, expose secrets, or weaken RLS.
