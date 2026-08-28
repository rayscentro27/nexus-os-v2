# Nexus V2 Real Component Map

| Registered loop | Real component(s) found | Connected to registered runner? | Canonical candidate | Finding |
|---|---|---:|---|---|
| telegram_operator | `scripts/operations/nexus_hermes_telegram_worker.py`; `scripts/telegram/nexus_telegram_bridge.py` | NO | Hermes Telegram worker for current control path | Registry points elsewhere; tested scope real |
| hermes_router | `scripts/nexus_agent_platform/control_object_resolver.py`; Hermes worker | NO | Hermes worker/control resolver | Tested route real; registry generic |
| system_health | `run_system_health_check`; shared capability | PARTIAL | `nexus_active_operator_runner.py` bounded function | Real bounded path, generic row |
| supabase_verification | bounded runner; `tests/e2e/supabase-real-world-certification.spec.ts`; governed client | PARTIAL | bounded runner + Playwright spec | Preflight real; campaign trigger absent |
| research_intelligence | `scripts/run_nexus_research_cycle.py`; `scripts/hermes/hermes_web_search.py` | NO | research cycle with explicit provider contract | Dry-run registry |
| repo_intelligence | repository study/index/report modules | NO | one repo-intelligence read runner | Miswired |
| alpha_intake | `scripts/alpha/alpha_telegram_worker.py`; alpha modules | NO | Alpha worker after authority review | Orphaned generation |
| client_portal_paywall_access | client portal/payment scripts; approval lanes | NO | gated client/revenue access control | Blocked by design |
| client_portal_status | `scripts/client_flow/*`; `src/lib/supabaseClient.ts`; client pages | NO | client portal read model | Static/synthetic fallbacks present |
| command_center_health | `scripts/automation/feeders/command_center_summary_feeder.py`; mission-control read model | NO | command-center read model | Miswired |
| creative_quality_loop | `scripts/creative/*`; `scripts/runner_handlers/creative_handlers.py` | NO | internal draft/review lane | Dry-run by design |
| credit_business_funding_readiness | `scripts/credit/*`; `scripts/client_flow/build_funding_readiness.py` | NO | canonical client/admin readiness workflow | P1 miswired |
| daily_monitor | `scripts/operations/nexus_daily_monitor.py`; `scripts/run_nexus_daily_monitor.py` | NO | one daily monitor script | Registry generic |
| marketing_content_pipeline | `scripts/marketing/*`; creative draft generators | NO | internal draft pipeline | Dry-run/external effect gated |
| notebooklm_import_status | `scripts/intake/notebooklm_connector.py` | NO | import adapter or merge into research | Dry-run |
| ray_review_queue | `scripts/review/build_ray_review_queue.py`; review modules | NO | governed review queue | P0 miswired |
| recovery | `scripts/operations/nexus_recovery_check.py` | YES | recovery check script | Real read-only implementation, stale registry evidence |
| stripe_test_paywall | `scripts/payments/*`; `scripts/approval_lanes/*` | NO | sandbox-only test lane | Disabled/blocked |
| work_orders | `scripts/nexus_agent_platform/governed/work_orders.py`; governed APIs | NO | governed work-order module | Registry generic |

## Duplicate generations and orphaning

The repository contains parallel generations of Telegram bridges, Hermes workers, Active Operator scripts, research scripts, client-flow builders, creative pipelines, and Supabase verification tools. The registry generally references the generic Active Operator runner rather than the specialized component. This is an architectural reconciliation problem, not evidence that every component is absent.

## Data-source warnings

- Local JSON/runtime reports are useful evidence only when freshness and lineage are checked.
- Client portal code contains synthetic/test-oriented paths and must not be scored as production client delivery without a live authenticated tenant proof.
- Research and NotebookLM artifacts include cached/exported material; cache existence is not current provider execution.
- Stripe paths are test/sandbox and disabled; they are not payment operation.
