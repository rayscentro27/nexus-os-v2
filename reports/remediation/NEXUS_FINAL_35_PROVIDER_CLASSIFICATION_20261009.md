# NEXUS FINAL 35 PROVIDER CLASSIFICATION — 2026-10-09

## Result

**OBSERVED FACT:** The current scanner finds 45 provider-like files; all 45 are now represented in the caller registry. The exact unregistered set was 35 files. The registry has zero BYPASS, PARTIAL, or UNKNOWN classifications.

**OBSERVED FACT:** Public web, YouTube, GitHub fallback, TradingView, commercial source, Printify catalog, credit-report Supabase, Creative Storage, Webull, and Temporal Supabase read calls identified in this pass now pass through job-scoped provider enforcement, or are explicitly disabled. Requests without durable job context are denied before the network operation.

**OBSERVED FACT:** Focused tests passed: provider enforcement + provider guard, 19 passed; runtime environment + Research privilege + provider enforcement + provider guard, 23 passed. Python compilation checks and `git diff --check` passed.

**LIMITATION:** This is local source/reachability evidence. It does not certify inaccessible remote administrative metadata. Nexus remains in safe mode; no runtime was activated.

## File classifications

| File | Provider/surface | Classification | Reachability and evidence | Secret names (if any) |
|---|---|---|---|---|
| `scripts/alpha/alpha_discovery.py` | BROWSER_EXTERNAL_SERVICES | GOVERNED | Public page and YouTube reads now pass execute_public_read; missing durable job context denies before transport. | None identified |
| `scripts/alpha/alpha_telegram_worker.py` | TELEGRAM | GOVERNED | Telegram delivery paths use execute_telegram_delivery/provider enforcement; research delegates to governed Alpha adapters. | ALPHA_TELEGRAM_BOT_TOKEN, ALPHA_TELEGRAM_CHAT_ID, TELEGRAM_CHAT_ID |
| `scripts/alpha/run_youtube_followup_worker.py` | YOUTUBE | GOVERNED | Follow-up retrieval calls the governed Alpha retrieval wrapper. | None identified |
| `scripts/client_flow/prepare_fake_customer_persistent_insert_execution.py` | SUPABASE | DISABLED_FAIL_CLOSED | Live execute/cleanup modes now raise a fail-closed error pending a durable governed job. | None identified |
| `scripts/client_flow/verify_fake_customer_records.py` | SUPABASE | NOT_APPLICABLE | Read-only Supabase CLI verification; manually invoked admin diagnostic, no autonomous entrypoint. | SUPABASE_CLI_AUTH_METADATA |
| `scripts/commercial/run_commercial_mission.py` | BROWSER_EXTERNAL_SERVICES | GOVERNED | Public-source fetch now uses execute_public_read and requires real job context. | None identified |
| `scripts/credit/parse_uploaded_credit_report.py` | SUPABASE | GOVERNED | Supabase REST and Storage requests now execute behind job-scoped governor. | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY |
| `scripts/hermes/hermes_web_search.py` | BROWSER_EXTERNAL_SERVICES | GOVERNED | Brave/Tavily/SerpAPI and public page reads use provider enforcement. | BRAVE_SEARCH_API_KEY, TAVILY_API_KEY, SERPAPI_KEY |
| `scripts/nexus_agent_platform/content_intelligence.py` | YOUTUBE | GOVERNED | YouTube metadata subprocess now passes execute_public_read; search delegates to governed proactive discovery. | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY |
| `scripts/nexus_agent_platform/creative/media_library.py` | SUPABASE | GOVERNED | Storage HTTP operations require durable job identity and governor reservation. | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY |
| `scripts/nexus_agent_platform/credential_control_plane.py` | BRAVE_SEARCH | GOVERNED | Brave health query delegates to governed Alpha HTTP adapter; Keychain access is metadata-driven. | NEXUS_CREDENTIAL_REGISTRY_REFERENCES, MACOS_KEYCHAIN_ITEMS |
| `scripts/nexus_agent_platform/marketing_creative_workflow.py` | LOCAL | NOT_APPLICABLE | Provider-like match is configuration/local workflow state; external calls delegate to separately governed adapters. | None identified |
| `scripts/nexus_agent_platform/oracle_gemma_certification.py` | LOCAL_AI | NOT_APPLICABLE | Only loopback Ollama-compatible endpoint; no external provider or spend path. | None identified |
| `scripts/nexus_agent_platform/providers/webull_provider.py` | WEBULL | GOVERNED | Read-only GET/HEAD API calls now use execute_public_read; other methods are denied by adapter. | WEBULL_APP_KEY, WEBULL_APP_SECRET |
| `scripts/nexus_agent_platform/research/last30days_adapter.py` | GITHUB | GOVERNED | Public fallback requests use execute_public_read and bounded response sizes. | None identified |
| `scripts/nexus_agent_platform/research_lane_scheduler.py` | LOCAL | NOT_APPLICABLE | Local lane selection only; it does not perform provider I/O. | None identified |
| `scripts/nexus_agent_platform/tradingview_public_source.py` | BROWSER_EXTERNAL_SERVICES | GOVERNED | TradingView public reads use execute_public_read. | None identified |
| `scripts/nexus_agent_platform/workflows/temporal_activities.py` | SUPABASE | GOVERNED | Supabase reads and Telegram/email actions use job-scoped execute_async/provider authorization. | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, TELEGRAM_BOT_TOKEN, NEXUS_TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_CHAT_IDS |
| `scripts/nexus_product_evolution/deployment.py` | NETLIFY | NOT_APPLICABLE | Read-only deployment health/admin diagnostics; no deploy or mutation command is invoked. | NETLIFY_CLI_AUTH_METADATA |
| `scripts/nova/nova_telegram_worker.py` | TELEGRAM | GOVERNED | Telegram send/receiver calls are gated by provider enforcement; no independent scheduler is enabled. | HERMES_NOVA_TELEGRAM_BOT_TOKEN, HERMES_NOVA_CHAT_ID, TELEGRAM_CHAT_ID |
| `scripts/operations/nexus_hermes_telegram_worker.py` | TELEGRAM | GOVERNED | Telegram send calls pass job-scoped provider enforcement. | TELEGRAM_BOT_TOKEN, NEXUS_TELEGRAM_BOT_TOKEN |
| `scripts/research/pulse_runtime.py` | BROWSER_EXTERNAL_SERVICES | GOVERNED | Public feeds and Printify catalog reads now use execute_public_read; publishing/order actions are statically disabled. | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, KEYCHAIN_ITEM:nexus.printify.api_token |
| `scripts/research/run_campaign_utilization.py` | LOCAL | NOT_APPLICABLE | Local campaign utilization report; no provider transport in this file. | None identified |
| `scripts/research/run_dispatched_research_job.py` | MULTI_PROVIDER | GOVERNED | Job entrypoint passes work to governed research adapters; no direct provider transport. | None identified |
| `scripts/research/run_three_mode_architecture_bakeoff.py` | BROWSER_EXTERNAL_SERVICES | GOVERNED | Research URL fetch now uses execute_public_read. | None identified |
| `scripts/run_nexus_continuous_operations.py` | MULTI_PROVIDER | LEGACY_DISABLED | Legacy continuous runtime remains disabled by the verified safe-mode configuration; individual email path uses enforcement. | LEGACY_DISABLED_RUNTIME_ENV_ALLOWLIST |
| `scripts/social/facebook_publisher.py` | META | GOVERNED | Public post path requires approval and execute provider boundary. | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, META_PAGE_ACCESS_TOKEN_REFERENCE |
| `scripts/social/facebook_token_status.py` | META | GOVERNED | Read-only Meta status request passes execute and is not a publish path. | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, META_PAGE_ACCESS_TOKEN_REFERENCE |
| `scripts/supabase/inspect_production_rls_policies.py` | SUPABASE | NOT_APPLICABLE | Manual read-only Supabase CLI schema diagnostic. | SUPABASE_CLI_AUTH_METADATA |
| `scripts/supabase/verify_production_rls_cli.py` | SUPABASE | NOT_APPLICABLE | Manual read-only Supabase CLI query diagnostic. | SUPABASE_CLI_AUTH_METADATA |
| `scripts/supabase/verify_production_schema_readonly.py` | SUPABASE | NOT_APPLICABLE | Manual read-only Supabase CLI schema/migration diagnostic. | SUPABASE_CLI_AUTH_METADATA |
| `scripts/telegram/nexus_telegram_bridge.py` | TELEGRAM | GOVERNED | Telegram calls use execute_telegram_delivery/execute; no auto-poll path is enabled. | SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, TELEGRAM_BOT_TOKEN, NEXUS_TELEGRAM_BOT_TOKEN |
| `scripts/trading/alpaca_options_capability_check.py` | ALPACA | GOVERNED | Read-only Alpaca calls delegate to governed Alpha HTTP adapter; live writes are absent. | ALPACA_API_KEY_REFERENCE, ALPACA_SECRET_KEY_REFERENCE, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY |
| `scripts/trading/oanda_demo_common.py` | OANDA | GOVERNED | Requests route through governed Alpha HTTP adapter and live endpoint is fail-closed. | OANDA_API_TOKEN_REFERENCE, OANDA_ACCOUNT_ID |
| `supabase/functions/hermes-search/index.ts` | MULTI_PROVIDER | DISABLED_FAIL_CLOSED | Function returns 503 governed_durable_job_required before parsing a request or calling providers. | None identified |

## Safe-mode and least-privilege disposition

**OBSERVED FACT:** The local secret registry contains 41 loader assessments; all 41 are classified `NARROW_SCOPED`, and the safe-mode process inventory reports zero active workflow processes. Research direct service-role access remains `NO`. Secret names and safe references only are recorded; no values were read or copied.

**INFERENCE:** Because no workflow process is active and registered loaders constrain keys by caller, no currently running Nexus worker has excess secret exposure. Service-role use remains a backend authority boundary and should continue to be narrowed to purpose-scoped database operations during later production hardening.

**UNKNOWN:** Inherited environment values cannot be independently enumerated without reading them; reports intentionally do not read or display values.

## Activation state

**OBSERVED FACT:** Scheduler, dispatcher, old continuous kernel, active operator, and certification remain OFF. This classification pass does not authorize activation.

## Closure scorecard

- Provider registry rows: **198**. Governed: **62**; disabled fail-closed: **10**; legacy disabled: **11**; not applicable: **10**; test/mock: **100**; static false positive: **5**; dead/unreachable: **0**.
- Bypass: **0**; partial: **0**; unknown: **0**; unregistered provider-like files: **0**.
- Local runtime env loader references: **41**; active process consumers: **0**; loader assessments classified narrow scoped: **41**.
- Local secret consumer mappings: **198**; unknown local consumers: **0**.
