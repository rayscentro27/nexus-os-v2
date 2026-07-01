# Nexus Section Status Report

**Generated:** 2026-07-01

## Summary

| Status | Count |
|--------|-------|
| Live | 6 |
| Static | 5 |
| Report Snapshot | 3 |
| Mismatch | 0 |
| Blocked | 0 |
| **Total** | **14** |

## Live Sections (6)

| Section | Source | Rows | Table | Proof | Process | Scheduler |
|---------|--------|------|-------|-------|---------|-----------|
| Hermes Workroom | supabase | 0 | — | verified | active | — |
| Ray Review | supabase | 62 | task_requests | verified | active | — |
| Business Opportunities | supabase | 26 | business_opportunities | verified | active | — |
| Research Engine | supabase | 52 | research_sources | verified | active | installed |
| Monetization | supabase | 9 | monetization_opportunities | verified | active | — |
| Clients | supabase | 1 | client_profiles | verified | active | — |

## Static Sections (5)

| Section | Source | Proof | Process | Scheduler | Notes |
|---------|--------|-------|---------|-----------|-------|
| Credit & Funding | local_static | no_proof | — | — | Static concept — no live Supabase table yet. Approval-gated workflow proposed. |
| Trading Lab | local_static | unproven | active | installed | Trading engine process active (pid-588), demo loop scheduler loaded, but paper/demo only. No live funded trading. |
| Settings | local_static | no_proof | — | — | Config presence checked by env name only. No secrets exposed. |
| Marketing Drafts | local_static | no_proof | — | — | Draft-only content. Approval-gated workflow proposed. |

## Report Snapshot Sections (3)

| Section | Source | Proof | Process | Scheduler | Notes |
|---------|--------|-------|---------|-----------|-------|
| System Health | local_static | unproven | — | — | Data from operations status reports. No dedicated Supabase table. |
| Automation Scheduler | local_static | unproven | active | installed | 26+ launchd schedulers installed and loaded. Process proof varies per scheduler. |
| Reports | local_static | unproven | — | — | Report files exist locally. Indexed in reports/ directory. |
| CLI / Tool Registry | local_static | unproven | — | — | 11 CLI tools inventoried. Safe/approval/blocked commands documented. |

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
2. Trading engine active but demo-only, no live funded trading
3. System Health — no dedicated Supabase table, report snapshot only
4. Automation schedulers loaded but no active PID proof for all
5. Reports center reads local files only
6. CLI registry no live Supabase table
7. Credit & Funding not wired to Supabase
8. Settings no dynamic Supabase table
9. Marketing Drafts no Supabase table

## Critical Note

Do not claim a section is live unless verified by Supabase read, process evidence, or log proof. If something is not proven, say "not proven live."
