# Live Seed Execution Report

**Date:** 2026-07-01T14:07:04Z
**Mode:** LIVE INSERT (--execute)
**Script:** scripts/supabase/seed_static_data_to_supabase.py

---

## Execution Summary

| Table | Parsed | Would Insert | Already Existed | Newly Inserted | Final Count |
|-------|--------|--------------|-----------------|----------------|-------------|
| task_requests (ray_review_item) | 64 | 62 | 62 | 0 | 62 |
| business_opportunities | 26 | 26 | 0 | 26 | 26 |
| monetization_opportunities | 9 | 9 | 9 | 0 | 11 |
| client_profiles | 1 | 1 | 1 | 0 | 1 |
| research_sources | 50 | 50 | 50 | 0 | 52 |
| nexus_events (receipt) | 1 | 1 | — | 1 | 580 |
| **Total** | **151** | **149** | **122** | **27** | **732** |

---

## Notes

- task_requests: 62 rows seeded in first execution (2026-07-01T14:03:50Z), skipped on re-run
- business_opportunities: Failed first run due to timestamp format, succeeded on second run with PostgreSQL default
- monetization_opportunities: 9 seeded in first execution, 2 pre-existing rows = 11 total
- client_profiles: 1 seeded in first execution, skipped on re-run
- research_sources: 50 seeded in first execution, 2 pre-existing rows = 52 total
- nexus_events: 580 total includes pre-existing system events + 1 seed receipt

## Schema Mapping

All data maps to ACTUAL Supabase schema columns:
- task_requests: `task_type='ray_review_item'`, card data in `payload` jsonb
- business_opportunities: `title`, `score`, `status`, `category` columns; extras in `payload` jsonb
- research_sources: `source_type`, `title`, `confidence` columns; extras in `metadata` jsonb
- monetization_opportunities: `title`, `status`, `decision` columns; extras in `metadata` jsonb
- client_profiles: `client_label`, `current_stage`, `progress_percentage` columns; extras in `metadata` jsonb

## Safety

- No real client PII inserted (only synthetic Julius Erving demo record)
- No destructive SQL executed
- No RLS policies weakened
- No external actions performed
- All records marked `data_source: static_import`, `synthetic: True`
