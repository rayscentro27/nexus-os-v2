# Nexus Manual Loop Certification

Generated: 2026-08-27T15:23:07.768915+00:00

| Loop | First | Verify | Second | Idempotency | Final |
|---|---|---|---|---|---|
| voice | PASS | PASS | True | PASS | VERIFIED_PASS |
| calendar | BLOCKED_EXTERNAL | FAIL | False | PASS | BLOCKED_EXTERNAL |
| research | PASS | PASS | True | PASS | VERIFIED_PASS |
| live_research | PASS | FAIL | False | PASS | BLOCKED_EXTERNAL |
| forex | PASS | PASS | True | PASS | VERIFIED_PASS |
| business | PASS | PASS | True | PASS | VERIFIED_PASS |
| visual | PASS | PASS | True | PASS | VERIFIED_PASS |
| creative | PASS | PASS | True | PASS | VERIFIED_PASS |
| health | PASS | PASS | True | PASS | VERIFIED_PASS |
| proof | PASS | PASS | True | PASS | VERIFIED_PASS |
| router | PASS | PASS | True | PASS | VERIFIED_PASS |
| product_evolution | PASS | PASS | True | PASS | VERIFIED_PASS |
| open_source_scout_loop | PASS | PASS | True | PASS | VERIFIED_PASS |
| research_intake_loop | PASS | PASS | True | PASS | VERIFIED_PASS |
| revenue_opportunity_loop | PASS | PASS | True | PASS | VERIFIED_PASS |
| seo_opportunity_loop | PASS | PASS | True | PASS | VERIFIED_PASS |

Scheduler was not used as certification evidence.

Special checks: failure self-repair=PASS; false-pass rejection=PASS; Product Evolution=PASS.
