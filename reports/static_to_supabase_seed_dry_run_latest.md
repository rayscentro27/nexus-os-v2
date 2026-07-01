# Static-to-Supabase Seed Dry-Run Report

**Date:** 2026-07-01T13:50:30.811241+00:00
**Mode:** DRY RUN

---

## Summary

| Table | Parsed | Would Insert | Skipped | Service Role |
|-------|--------|--------------|---------|--------------|
| `task_requests` | 64 | 62 | 2 | No |
| `business_opportunities` | 26 | 26 | 0 | No |
| `monetization_opportunities` | 9 | 9 | 0 | No |
| `client_profiles` | 1 | 1 | 0 | No |
| `research_sources` | 50 | 50 | 0 | Yes |
| **Total** | | **148** | **2** | |

---

## Schema Mapping Notes

The actual Supabase schema uses generic columns (`payload` jsonb, `metadata` jsonb) rather than
the specific columns the original seed plan assumed. This script correctly maps:

- **task_requests**: `task_type='ray_review_item'`, card data in `payload` jsonb
- **business_opportunities**: `title`, `score`, `status`, `category` as columns; extra fields in `payload` jsonb
- **research_sources**: `source_type`, `title`, `confidence` as columns; extra fields in `metadata` jsonb
- **monetization_opportunities**: `title`, `status`, `decision` as columns; extra fields in `metadata` jsonb
- **client_profiles**: `client_label`, `current_stage`, `progress_percentage` as columns; extra fields in `metadata` jsonb

---

## Table Details

### `task_requests`

- Static source: `src/data/rayReviewData.js`
- Parsed: 64 records
- Would insert: 62
- Skipped: 2
- RLS policy: nexus_is_active_admin()

### `business_opportunities`

- Static source: `src/data/businessOpportunitiesData.js`
- Parsed: 26 records
- Would insert: 26
- Skipped: 0
- RLS policy: nexus_is_active_admin()

### `monetization_opportunities`

- Static source: `src/data/monetizationData.js`
- Parsed: 9 records
- Would insert: 9
- Skipped: 0
- RLS policy: nexus_is_active_admin()

### `client_profiles`

- Static source: `src/data/clientsData.js`
- Parsed: 1 records
- Would insert: 1
- Skipped: 0
- RLS policy: nexus_is_active_admin()

### `research_sources`

- Static source: `src/data/researchEngineData.js`
- Parsed: 50 records
- Would insert: 50
- Skipped: 0
- RLS policy: admin_users.active = true (no anon INSERT)
