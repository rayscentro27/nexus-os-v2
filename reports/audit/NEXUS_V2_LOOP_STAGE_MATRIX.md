# Nexus V2 Loop Stage Matrix

Codes: `RP` REAL_PASS, `RPa` REAL_PARTIAL, `INP` IMPLEMENTED_NOT_PROVEN, `MW` MISWIRED, `SIM` SIMULATED, `DRY` DRY_RUN, `STALE` STALE_EVIDENCE, `CFG` CONFIG_ONLY, `BBD` BLOCKED_BY_DESIGN, `NIM` NOT_IMPLEMENTED, `NA` NOT_APPLICABLE, `UNK` UNKNOWN.

| Loop | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| telegram_operator | RP | RP | RP | RP | NA | NA | INP | NA | RP | NA | INP | NA | NA | RP | NA | RP | RP | RP |
| hermes_router | RP | RP | RP | RP | NA | NA | NA | NA | RP | NA | NA | NA | NA | RP | NA | RP | RP | RP |
| system_health | RP | RP | RP | RP | NA | NA | NA | NA | RP | NA | NA | NA | NA | RP | NA | RP | RP | RP |
| supabase_verification | RPa | RPa | INP | INP | INP | INP | NA | NA | INP | INP | NA | NA | NA | INP | INP | INP | INP | INP |
| research_intelligence | DRY | DRY | MW | INP | INP | INP | DRY | INP | DRY | INP | NA | NA | NA | DRY | INP | DRY | INP | DRY |
| repo_intelligence | MW | MW | MW | INP | NA | NA | INP | NA | MW | NA | NA | NA | NA | INP | NA | MW | INP | MW |
| alpha_intake | MW | MW | MW | INP | INP | INP | INP | INP | MW | INP | NA | NA | NA | INP | INP | MW | INP | MW |
| client_portal_paywall_access | BBD | BBD | BBD | BBD | INP | INP | NA | NA | BBD | BBD | NA | NA | NA | INP | BBD | BBD | INP | BBD |
| client_portal_status | MW | MW | INP | INP | INP | INP | NA | NA | MW | INP | NA | NA | NA | INP | INP | MW | INP | MW |
| command_center_health | MW | MW | MW | INP | NA | NA | INP | NA | MW | INP | NA | NA | NA | INP | NA | MW | INP | MW |
| creative_quality_loop | DRY | DRY | INP | INP | NA | NA | DRY | INP | DRY | DRY | NA | NA | NA | INP | NA | DRY | INP | BBD |
| credit_business_funding_readiness | MW | MW | INP | INP | INP | INP | NA | INP | MW | INP | NA | NA | NA | INP | INP | MW | INP | MW |
| daily_monitor | MW | MW | MW | INP | NA | NA | INP | NA | MW | NA | NA | NA | NA | INP | NA | MW | INP | MW |
| marketing_content_pipeline | DRY | DRY | INP | INP | NA | NA | DRY | INP | DRY | DRY | NA | NA | NA | INP | BBD | DRY | INP | BBD |
| notebooklm_import_status | DRY | DRY | MW | INP | INP | INP | DRY | INP | DRY | INP | NA | NA | NA | DRY | INP | DRY | INP | DRY |
| ray_review_queue | MW | MW | MW | INP | INP | NA | INP | NA | MW | NA | NA | RP | NA | INP | NA | MW | INP | MW |
| recovery | RPa | RPa | RPa | RPa | NA | NA | NA | NA | RPa | NA | RP | NA | NA | RPa | NA | RPa | INP | RPa |
| stripe_test_paywall | BBD | BBD | BBD | BBD | INP | INP | NA | NA | BBD | BBD | NA | NA | NA | INP | BBD | BBD | INP | BBD |
| work_orders | MW | MW | INP | RP | RP | NA | INP | NA | MW | NA | NA | RP | NA | INP | NA | MW | INP | MW |

For every non-pass cell, the governing reason is one of: generic registry runner, simulated/dry-run receipt, stale/static artifact, missing fresh real trigger, intentionally blocked external effect, or implementation existing outside the registered loop. Details are in the main report and component map.
