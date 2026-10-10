# Nexus final three provider and local secret closure — 2026-10-09

## Remote provider paths

**OBSERVED FACT:** Authenticated GitHub CLI listed `Render Short Video Maker (artifact only)` as active in `rayscentro27/nexuslive`; workflow ID `291709925` was disabled manually. A subsequent remote listing reported `disabled_manually`. Its workflow file remains preserved in the repository for review/rollback. It had only `workflow_dispatch`, fetched Pexels content, and uploaded a render artifact.

**OBSERVED FACT:** The production deployment owner was identified from canonical `netlify.toml`, the `nexus-os-v2` Git remote, and unauthenticated read-only Netlify site/deploy metadata: site `nexusv20`, domain `goclearonline.cc`, repo `rayscentro27/nexus-os-v2`, production branch `main`. No Netlify CLI deployment was used.

**OBSERVED FACT:** Canonical fail-closed TikTok and Firecrawl sources were pushed through the established GitHub `main` → Netlify production path. Final production deployment `6ac961d42a09190008b7ac16` is `ready` for commit `67c48700bdaf763a74dc4c4fb485189bd8727524`.

**OBSERVED FACT:** Safe public checks returned HTTP 503 with `disabled_fail_closed` for `/api/alpha/url-review`, TikTok auth-start, OAuth callback, refresh, and disconnect routes. The route handlers return before Firecrawl/TikTok network access. No provider call was made. Native Node no-network tests passed (3).

**OBSERVED FACT:** The three old remote registry bypass rows are now `DISABLED_FAIL_CLOSED`; three direct TikTok OAuth lifecycle calls discovered in route source were also removed and recorded as disabled. Registry rows: 163; reviewed row counts: governed=39, disabled=8, legacy-disabled=10, not-applicable=1, test/mock=100, static false positives=5, dead=0, bypass=0, partial=0, row-unknown=0.

## Secret scoping

**OBSERVED FACT:** Python runtime credential loading remains deny-by-default for sensitive values and uses explicit per-caller allowlists. The JavaScript runtime loader now denies sensitive keys by default; certification can load only the public Supabase anon key from the common runtime file and explicit E2E credentials from the E2E file. Service-role access is unavailable through that certification loader.

**OBSERVED FACT:** Alpha live Research no longer loads or uses Supabase service-role credentials. Its legacy direct Supabase write methods now fail closed with `durable_job_backend_required`; local research artifact output remains available. `RESEARCH_SUPABASE_SERVICE_ROLE_DIRECT_ACCESS=NO`.

**OBSERVED FACT:** `.env` parsing in the social Supabase adapter and handoff client is restricted to the Supabase URL/key allowlist. The local metadata registry has 41 loader references with 41 safe-metadata assessments; no secret values were read.

**UNKNOWN:** `UNKNOWN_LOCAL_SECRET_CONSUMERS=NOT_CERTIFIED_ZERO`. Static identifier scans do not prove all dynamic or inherited process environment consumers. Remaining durable-control-plane/service-role consumers have not been narrowed per operation, so `OVERPRIVILEGED_LOCAL_WORKERS` and `UNNECESSARY_LOCAL_SECRET_EXPOSURE` are not certified zero.

## Whole-source caller guard

**OBSERVED FACT:** `provider_surface_guard.py` scans executable Python/JS/TS/MJS/CJS and workflow source for direct HTTP expressions, SDK construction, provider/cloud CLI calls, and browser external actions. It skips tests/mocks/fixtures/generated trees and the approved enforcement wrappers; its self-tests cover direct requests, fetch, SDK, wrapper, mock and string-only cases. Focused suite passed (22 tests); Node fail-closed suite passed (3 tests); syntax checks and `git diff --check` passed.

**OBSERVED FACT:** The scan found 45 provider-like source files. 35 files have no caller rows in the registry. The guard correctly fails on those unregistered files, so `PROVIDER_BYPASS_REGRESSION_GUARD=NO` for the current repository state, despite new-file discovery and fail-on-unregistered behavior being implemented. These need caller-by-caller review before activation.

## Runtime state and decision

**OBSERVED FACT:** Scheduler, dispatcher, old continuous kernel, active operator, and certification remain OFF. No provider workload was started.

**DECISION:** `INTERNAL_PRE_ACTIVATION_ZERO_UNKNOWN_PASS=NO`; the three named remote bypasses are closed, but whole-source caller coverage and least-privilege closure remain incomplete. `FINAL_STATUS=NEXUS_TRACK_A_FINAL_CLOSURE_NOT_READY`.


## Unregistered provider-like source surfaces

**OBSERVED FACT:** The source scanner identified these 35 files as provider-like but not represented in caller rows. Scanner matches need caller-level classification; they are not asserted to be 35 active bypasses. They remain activation-gate unknowns until classified.

- `scripts/alpha/alpha_discovery.py`
- `scripts/alpha/alpha_telegram_worker.py`
- `scripts/alpha/run_youtube_followup_worker.py`
- `scripts/client_flow/prepare_fake_customer_persistent_insert_execution.py`
- `scripts/client_flow/verify_fake_customer_records.py`
- `scripts/commercial/run_commercial_mission.py`
- `scripts/credit/parse_uploaded_credit_report.py`
- `scripts/hermes/hermes_web_search.py`
- `scripts/nexus_agent_platform/content_intelligence.py`
- `scripts/nexus_agent_platform/creative/media_library.py`
- `scripts/nexus_agent_platform/credential_control_plane.py`
- `scripts/nexus_agent_platform/marketing_creative_workflow.py`
- `scripts/nexus_agent_platform/oracle_gemma_certification.py`
- `scripts/nexus_agent_platform/providers/webull_provider.py`
- `scripts/nexus_agent_platform/research/last30days_adapter.py`
- `scripts/nexus_agent_platform/research_lane_scheduler.py`
- `scripts/nexus_agent_platform/tradingview_public_source.py`
- `scripts/nexus_agent_platform/workflows/temporal_activities.py`
- `scripts/nexus_product_evolution/deployment.py`
- `scripts/nova/nova_telegram_worker.py`
- `scripts/operations/nexus_hermes_telegram_worker.py`
- `scripts/research/pulse_runtime.py`
- `scripts/research/run_campaign_utilization.py`
- `scripts/research/run_dispatched_research_job.py`
- `scripts/research/run_three_mode_architecture_bakeoff.py`
- `scripts/run_nexus_continuous_operations.py`
- `scripts/social/facebook_publisher.py`
- `scripts/social/facebook_token_status.py`
- `scripts/supabase/inspect_production_rls_policies.py`
- `scripts/supabase/verify_production_rls_cli.py`
- `scripts/supabase/verify_production_schema_readonly.py`
- `scripts/telegram/nexus_telegram_bridge.py`
- `scripts/trading/alpaca_options_capability_check.py`
- `scripts/trading/oanda_demo_common.py`
- `supabase/functions/hermes-search/index.ts`
