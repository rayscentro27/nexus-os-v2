# Nexus Current-State Inventory

Generated: 2026-08-17 · Commit baseline: `2aab745` · Client Portal V2: COMPLETE / PROTECTED

This inventory maps the 19 capability areas required by the Hermes Modernization Phase 0 audit. It is grounded in code inspection, not assumption. Every item carries real file paths.

## 0. Environment truth

- **HEAD** = `2aab745` (Client Portal V2 completed + auth-gate repair). Audit began on a clean checkout of this commit.
- Working tree contains pre-existing uncommitted edits to `scripts/nexus_agent_platform/contracts/dispatcher.py` (+ a new test). These are NOT part of this audit's changes and will not be committed by it.
- Many runtime-generated files (`data/alpha/intake/*`, `reports/alpha/*`, `reports/runtime/*`, `data/runtime/*`, `tmp/*`) are untracked. They are runtime artifacts, not source. The audit does not discard them.
- `E2E_PERSONA_*` / `E2E_ADMIN_*` credentials are not present in this environment. `guided-client-portal-certification` therefore cannot run here. Recorded as ENV_BLOCKED_E2E; does not block this sprint.

## 1. Python processes (deterministic core)

~630 `.py` files exist across `scripts/`, `nexus_research/`, `hermes_alpha/`. The distinct entry-point processes (not counting every module):

| Process | Path | Deterministic | Supabase writes | Schedule |
|---|---|---|---|---|
| continuous operations | `scripts/run_nexus_continuous_operations.py` | yes | events/receipts | manual |
| operational cycle (legacy 2h) | `scripts/run_nexus_operational_cycle.py` | yes | no | legacy |
| business activation | `scripts/run_nexus_business_activation.py` | yes | no | manual |
| daily monitor | `scripts/run_nexus_daily_monitor.py` | yes | no | manual |
| overnight safe ops | `scripts/run_nexus_overnight_safe_ops.py` | yes | optional events | manual |
| daily closeout (stub) | `scripts/run_nexus_daily_closeout.py` | yes | no | superseded |
| research cycle (stub, disabled) | `scripts/run_nexus_research_cycle.py` | yes | no | disabled plist |
| social publish worker | `scripts/run_social_publish_job.py` | yes | `agent_jobs` | registry, disabled |
| job runner | `scripts/nexus_runner.py` | yes | `agent_jobs`, heartbeats | manual |
| continuous loop | `scripts/activation/run_nexus_continuous_loop.py` | yes | no | launchd 30m (running) |
| full activation | `scripts/activation/run_nexus_full_activation.py` | yes | staging only | via loop |
| daily operating cycle | `scripts/activation/run_daily_operating_cycle.py` | yes | no (subprocess) | launchd 08:00 |
| evening closeout cycle | `scripts/activation/run_evening_closeout_cycle.py` | yes | no (subprocess) | launchd 18:00 |
| registry consumer | `scripts/activation/run_automation_schedule_registry.py` | yes | staging only | via loop |
| department feeder | `scripts/automation/run_department_feeder.py` | yes (dry-run AI) | yes events | manual |
| department digest | `scripts/automation/run_daily_department_digest.py` | yes | yes events | manual |
| night internal tests | `scripts/night_run/run_all_night_internal_tests.py` | yes | no | manual |
| active operator runner | `scripts/operations/nexus_active_operator_runner.py` | yes | yes telemetry | launchd hourly |
| recovery check | `scripts/operations/nexus_recovery_check.py` | yes | no (local WOs) | launchd |
| system monitor | `scripts/operations/nexus_daily_monitor.py` | yes | no | manual |

**Key fact:** every enabled schedule in `configs/automation_schedule_registry.json` (~70 entries) is `internal_safe` and deterministic. `configs/safe_scheduler_policy.json` forbids external actions, DB writes, email, SMS, social publish, live trading, and Stripe live. This is a deterministic-first system already.

## 2. Hermes

`scripts/nexus_agent_platform/agents/hermes.py` — CEO-advisor Telegram agent with two layers: a conversational front brain (`agents/front_brain.py`, LLM intent classification against `CERTIFIED_READS`/`CERTIFIED_ACTIONS`, deterministic fuzzy fallback) plus a governed execution engine. Perspective context in `context/hermes_store.py` (TTL 1h, provenance-projected fields only).

Default model `openai/gpt-4o-mini` via `workflows/litellm_adapter.py` (LITELLM gateway flag off; OpenRouter fallback).

## 3. Nova

`scripts/nexus_agent_platform/agents/nova.py` (~171 KB) — isolated conversational agent with its own memory namespace, own LangGraph, own Telegram bot token, OpenRouter model, Langfuse trace namespace. Read-only Supabase boundary enforced by allowlist `capabilities/shared.py` (`NOVA_ALLOWED_READS`, `_UNSAFE_FIELDS` redaction). No Supabase writes, no OANDA, no Temporal, no Hermes/Alpha memory access by contract. Deterministic pre-model semantic capability gate: `capabilities/nexus_query_planner.py` (`plan_query` → `validate_plan` → execute; deterministic fallback plan). Live launchd `com.nexus.telegram-hermes-nova` at 30s ticks.

## 4. Alpha

`scripts/nexus_agent_platform/agents/alpha.py` — independent research advisor over Telegram. `scripts/alpha/alpha_live_research.py` — live research bridge (Brave search + YouTube Data API + OpenRouter synthesis, deterministic fallback) writing `nexus_process_runs`/`nexus_research_runs`/`nexus_research_results`/`business_opportunities`. Runtime artifacts: `data/alpha/intake/*.json`, `data/alpha/missions/*.json`, `reports/alpha/{research_results,opportunities,scores,briefs}/`. Alpha contract: no client PII.

`hermes_alpha/` is documentation/intake structure only (research inbox lanes + phase-1 evaluations); no research engine lives there.

## 5. LangGraph

Dependency REAL and installed (`langgraph 1.2.10` in `.venv-agent-platform`). Graphs defined via Nexus-owned wrapper `adapters/graph_adapter.py` (`StateGraph` behind `NEXUS_*_LANGGRAPH_ENABLED` flags, synchronous fallback when off):

- Hermes: `front_brain_classify → resolve_context → route_by_mode → execute_by_mode → compose_response` (+ legacy regex graph fallback, default on)
- Alpha: `classify_intent → research_decision → execute_research → synthesize_findings → compose_advisory`
- Nova: `classify_intent → handle_utility → capability_gate → build_context → generate_response → validate_output → compose_output`

**No LangGraph graphs exist for credit reasoning / outcome verification / funding reasoning** — those are deterministic Python + SQL (`credit_repair_workflow_v1.sql`, `credit_repair_case_engine.sql`, `strategy_outcome_analytics.sql`). That is the correct deterministic-first posture.

## 6. Temporal

`requirements-agent-platform.txt` declares `temporalio>=1.31.0`; real in `.venv-agent-platform`. `workflows/temporal_workflows.py` defines `ScheduledReportWorkflow`, `ApprovedEmailWorkflow`, `MissionRecoveryWorkflow` (flag-gated, direct-invoke fallback). Local temporal dev server at `~/.temporal` with `com.nexus.temporal-server`/`com.nexus.temporal-worker` loaded. Temporal currently schedules reports/emails/recovery only — not credit/funding lifecycles (those stay SQL/procedural).

## 7. Supabase

42 migration files. Relevant tables: `approvals`, `tenant_memberships`, `admin_users`, `client_profiles`, `agent_jobs`, `nexus_events`, `task_requests`, `nexus_process_runs`, `business_opportunities`, `monetization_opportunities`, `seo_opportunities`, `opportunity_experiments`, `research_runs`, `research_sources`, `model_routes`, `model_providers`, `model_usage_logs`, `agent_registry`, `approved_knowledge`, `worker_heartbeats`, `client_documents`, credit strategy/evidence tables, `ops_incidents`.

**NOT present** in SQL: `work_orders`, `agent_events`, `agent_requests`, `agent_runs`, `loop_runs`, `automation_runs`, `opportunities` (exact name), `daily_briefs`, `action_registry`, `audit_logs`. Work orders/approvals/audit are authoritative in local append-only JSONL (`data/governed/` via `scripts/nexus_agent_platform/governed/persistence.py`). This split (Supabase events vs. local governed JSONL) is a real architectural tension to note, not to destabilize.

RLS: 114 tables with RLS enabled, 208 `create policy` statements, security-definer `nexus_is_active_admin()`, `goclear_handle_new_user()`, `request_credit_analysis_rerun()`. Client data is tenant-scoped and self-select protected.

## 8. Governance

Authoritative governed loop: `scripts/nexus_agent_platform/governed/` — `approvals.py` (single-use consumption, 30-min default TTL, binding to one action), `policy_gate.py` (10 deterministic checks), `engine.py` (single entry, consumes approval on success, no auto-launch), `executors.py` (allowlist), `queue.py` (checkpoint-required claims), `action_registry.py` (LOW-risk executable set; PROHIBITED = live stripe, git push, netlify deploy, client sends, schema migration), `work_orders.py` (state machine + idempotency keys), `persistence.py` (append-only JSONL). Tests: `scripts/nexus_agent_platform/tests/test_governed_ops.py`.

Legacy file/UI approval system also exists (`scripts/approval/`, `scripts/approval_lanes/`). Schema-vs-code gap: the SQL `approvals` table has no TTL/single-use enforcement; those semantics live only in the Python governed layer.

## 9. Work orders

`scripts/nexus_agent_platform/governed/work_orders.py` — `VALID_STATUSES`, `ALLOWED_TRANSITIONS` map, idempotency (`idempotency_key_executed` blocks replay), stale detection. Runtime artifacts at `reports/work_orders/`. No SQL table (see §7).

## 10. Approvals

Single-use + TTL in `governed/approvals.py` (`DEFAULT_APPROVAL_TTL_SECONDS=30*60`, `mark_approval_consumed`, auto-expire sweep). Config policy in `configs/cli_safety_policy.json` and `configs/nexus_tool_access_registry.json` (43 tools; default-deny external; striple/gh/supabase/netlify/vercel approval-gated).

## 11. Runtime telemetry

`nexus_process_runs`/`nexus_process_definitions` (authoritative run registry, `20260803120000_authoritative_process_run_registry.sql`), `worker_heartbeats`, `nexus_events`, `model_route_decisions`, local `reports/runtime/*` + `scripts/reports/runtime/action_receipts`.

## 12. Telegram

Polling only (no webhook anywhere). `scripts/telegram/nexus_telegram_bridge.py` (`getUpdates` offset-driven, `--once`), `scripts/nova/nova_telegram_worker.py` (long-poll/`--once`), `scripts/alpha/alpha_telegram_worker.py`. Live launchd: `com.nexus.telegram-hermes-nova` (30s). Templates `com.nexus.telegram-hermes.plist.template` / `com.nexus.oanda-practice-trading.plist.template` point at a stale `nexus-os-v2-activation-20260804T014509Z` path. Telegram rotation report flags old plists as `UNSAFE_SECRETS_EXPOSED`. Production Telegram continues until a Gateway proves parity.

## 13. Model / provider routing

`scripts/model_router.py` — deterministic policy router (regex task_type + sensitivity → route from `[deterministic, local_private, manual, free_public_cloud, premium_cloud]`). Sensitive credit/funding/trading never reaches public cloud. Writes `model_route_decisions`. DB-backed config in `0003_premium_foundation.sql` + `0007_model_router_and_hermes_routes.sql`. Seeded routes (`seed_day7_model_router.py`): deterministic_nexus_scripts, manual_* (claude/opencode/codex), ollama/lm_studio local_private, openrouter_free_public_research, blocked_sensitive_public_cloud. No premium-cloud route active/approved. Any "builders" (OpenCode/MiMo) map to the manual_* routes.

## 14. Research infrastructure

External web-search harness `scripts/hermes/hermes_web_search.py` (brave → tavily → serpapi → searxng) — **provider abstraction exists, zero keys configured** (`reports/hermes/hermes_internet_search_audit_latest.md`). Netlify functions `netlify/functions/alpha-search.mjs` (SearXNG), `alpha-url-review.mjs` (Firecrawl), `alpha-provider.mjs` (OpenRouter/Groq) — exist, unconfigured.

Deterministic research that RUNS today: YouTube metadata (`youtube_api_metadata_refresh`, 12h), transcript availability/review (approved local TXT only, no media download), research source scout/scoring (`run_research_source_discovery.py --safe-internal`), NotebookLM import lanes, repo concept extraction, `cost` conversion pipelines (`build_research_to_*_pipeline.py`), `money_opportunity_model.py`. `configs/research_source_registry.json` (18 lanes) governs approved sources.

Multimodal: transcript metadata + `data/sources/youtube_transcripts/{approved,pending}` exists; `youtube_ytdlp_local_probe` requires approval (no media downloads by default — `downloads_media: false`).

## 15. Marketing infrastructure

Deterministic registers: `configs/offer_registry.json` (9 offers), `configs/stripe_product_registry.json` (test_only, 4 products), `configs/revenue_funnel_registry.json` (10-stage funnel, external_actions false), `configs/content_marketing_policy.json`, `configs/communication_safety_policy.json`, `configs/message_template_registry.json`. Scripts: `scripts/marketing/` (content calendar, landing page experiments, lead magnets, newsletter drafts), `scripts/creative/` (design variants, campaign assets, creative approvals), `scripts/social/` (Facebook publisher, gated), `scripts/monetization/` (offer/stripe/revenue builders, lead reactivation), `scripts/partners/` (affiliate reviews, disclosure checks).

## 16. Client portal integration points

Client Portal V2 (`src/client-v2/`) is **PROTECTED**. Entry points: `hooks/useV2ClientData.ts` consumes `src/lib/clientPortalDataAdapter.ts` (live Supabase, demo fallback), `clientJourneyModel.ts`, `clientFundingReadiness.ts`, `customerFlowEngine.ts`, `clydeActionEngine.ts`, `clydeContextEngine.ts`, `clientStageModel.ts`, `clientAuthContext.ts`. Live queues/boards: `credit_repair_workflow`, `readiness_review`, `tester_*` flows in `src/lib/creditRepairCaseEngine.ts` etc. A Vault contract exists (`src/config/clientVaultContract.ts`, `src/lib/clientVaultAdapter.ts`) with mock-only backend — `not_connected_by_design`.

## 17. Admin command center

Frontend: React 18 + Vite, path-string routing in `src/app/App.tsx` (no react-router). Existing Command Center: `src/components/CommandCenter.jsx`, `src/components/command-center/MissionControl.tsx` (`CommandCenterMissionControl`), backed by `src/lib/executive/executiveCommandCenterAdapter.ts`. `NexusAdminUI.jsx` sidebar has 23 panel ids including `command`, `opportunity`, `research`, `monetization`, `revenue-activation`, `automation`. Route registry: `src/components/Shell.tsx` `NAV` (16 keys), `src/config/nexusTabs.ts`. A tactical `command-center-v2` surface does NOT exist yet; existing panels are the integration target for Mission Control V2 (Phase 16).

## 18. Existing schedulers

Two layers: (a) launchd via `scripts/ops/*.sh` runners (`run_nexus_continuous_loop.py`, daily operating @08:00, evening closeout @18:00, active-operator hourly, recovery-check) and (b) `configs/automation_schedule_registry.json` consumed by `run_automation_schedule_registry.py --run-loop-safe`. Current live launchd: continuous-loop (running), telegram-hermes-nova (running), telegram-alpha (loaded, exit -9), oanda-practice (loaded, exit -9).

## 19. Existing business/revenue processes

Stripe: everything test-only (`test_session_open_unpaid`, `draft_not_created`, all fixtures/invoices synthetic). Revenue funnel registry stages run `Ray_approval → test_checkout → payment_confirmation → synthetic_onboarding → GoClear_review → client_delivery`. Trading: OANDA practice-only (`nexus_oanda_practice_engine.py` restricted to api-fxpractice). No live money automation anywhere.

---

## Existence summary (fast scan)

| Capability area from master prompt | Status |
|---|---|
| Python deterministic core | EXIST (extensive, protected) |
| Hermes agent runtime | EXIST (agent platform, flags-gated) |
| Nova runtime | EXIST (isolated, running) |
| Alpha external research | EXIST (bounded research + Telegram worker) |
| LangGraph | EXIST (3 linear graphs; no credit/outcome/funding graphs — deterministic keeps those) |
| Temporal | EXIST (report/email/recovery workflows) |
| Supabase + RLS | EXIST (strong) |
| Governance (approvals TTL/single-use, work orders, action registry) | EXIST (Python governed layer) |
| Model/provider routing | EXIST (deterministic policy router) |
| Telegram | EXIST (polling; production preserved) |
| Research infra | PARTIAL (YouTube/NotebookLM deterministic real; web-search/url-review harnesses unconfigured keys) |
| Marketing/revenue registers | EXIST (deterministic, all test-only money) |
| Client Portal V2 | EXIST (PROTECTED, complete) |
| Admin command center | EXIST (V1 panels; V2 surface does not exist yet) |
| Message bus tables (agent_requests/agent_events/opportunities) | PARTIAL (task_requests, nexus_events, business_opportunities exist; exact names don't) |
| Python capability registry | NOT_FOUND (largest Phase-0→1 gap; covered by capabilities/registry.py in nascent form) |
| Skills concept | NOT_FOUND (capability registry is the closest analog) |
| Loop framework | NOT_FOUND (schedule registry + governed queue are precursors) |
| Opportunity Engine data model | PARTIAL (business_opportunities + alpha opportunity scores exist) |
| Creative Lab | PARTIAL (creative department scripts exist; no research-before-creation rule enforced) |
| Cost observability | PARTIAL (model_route_decisions, model_usage_logs; no aggregated cost UI) |

This inventory is the authoritative answer to "what do we already have." Nothing below is a replacement for existing functionality; it is an extension.