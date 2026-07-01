# Nexus Section Status Report

**Generated:** 2026-07-01

## Summary

| Status | Count |
|--------|-------|
| Live | 5 |
| Static | 7 |
| Mismatch | 0 |
| Blocked | 0 |
| Unknown | 0 |
| **Total** | **14** |

## Live Sections (5)

| Section | Source | Rows | Table | Proof |
|---------|--------|------|-------|-------|
| Hermes Workroom | supabase | 0 | — | verified |
| Ray Review | supabase | 62 | task_requests | verified |
| Business Opportunities | supabase | 26 | business_opportunities | verified |
| Research Engine | supabase | 52 | research_sources | verified |
| Monetization | supabase | 9 | monetization_opportunities | verified |
| Clients | supabase | 1 | client_profiles | verified |

## Static Sections (7)

| Section | Source | Proof | Notes |
|---------|--------|-------|-------|
| Credit & Funding | local_static | no_proof | Not wired to Supabase |
| Trading Lab | local_static | no_proof | Scheduler loaded, not confirmed running |
| System Health | local_static | no_proof | Not wired to Supabase |
| Automation Scheduler | local_static | unproven | launchd loaded, no PID proof for all |
| Reports | local_static | no_proof | Local files only |
| Settings | local_static | no_proof | No dynamic Supabase table |
| CLI / Tool Registry | local_static | unproven | Local tool inventory only |
| Marketing Drafts | local_static | no_proof | Draft-only content |

## Research Engine — Detailed Status

- **Live research_sources count:** 52
- **YouTube research proof:** not_proven_live
- **Scheduler installed:** yes
- **Scheduler running:** not confirmed
- **Supabase write proof:** yes
- **Last report:** 2026-07-01
- **Watched channels:** 4
- **Blockers:** YouTube research not proven live — no process/log/write proof

## Blockers

1. YouTube research not proven live — no process/log/write proof
2. Credit & Funding not wired to Supabase
3. Trading Lab scheduler loaded but not confirmed running
4. System Health not wired to Supabase
5. Automation schedulers loaded but no active PID proof for all
6. Reports center reads local files only
7. Settings no dynamic Supabase table
8. CLI registry no live Supabase table
9. Marketing Drafts no Supabase table

## Critical Note

Do not claim a section is live unless verified by Supabase read, process evidence, or log proof. If something is not proven, say "not proven live."
