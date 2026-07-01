# Static-to-Supabase Seed Plan

**Date:** 2026-07-01
**Status:** Dry-run only — no live inserts
**Purpose:** Move bundled static data into Supabase tables so live-first loader returns live rows instead of fallback

---

## Overview

Nexus OS v2 currently uses 4 main data sources as static fallback. This plan maps each source to its Supabase target table, defines the column mapping, and provides a dry-run SQL script.

**Do NOT execute the seed SQL until explicitly approved via Ray Review.**

---

## Source → Table Mapping

| Static Source | File | Count | Supabase Table | RLS Policy |
|---|---|---|---|---|
| businessOpportunities | `src/data/businessOpportunitiesData.js` | 26 | `business_opportunities` | INSERT via `nexus_is_active_admin()` |
| researchCandidates | `src/data/researchEngineData.js` | 50 | `research_sources` | Service role only (no anon INSERT) |
| offers | `src/data/monetizationData.js` | 9 | `monetization_opportunities` | INSERT via `nexus_is_active_admin()` |
| clientsList | `src/data/clientsData.js` | 1 | `client_profiles` | INSERT via `nexus_is_active_admin()` |

---

## Column Mapping

### business_opportunities

| Static Field | Supabase Column | Type | Notes |
|---|---|---|---|
| id | id | uuid | Generate new UUID; keep static id as `legacy_id` |
| title | title | text | Direct map |
| category | category | text | Direct map |
| score | score | integer | Direct map |
| revenueRange | revenue_range | text | snake_case |
| confidence | confidence | text | Direct map |
| status | status | text | Direct map |
| reason | reason | text | Direct map |
| lane | lane | text | Direct map |
| nextAction | next_action | text | snake_case |
| convertOptions | convert_options | jsonb | Array stored as JSONB |
| createdAt | created_at | timestamptz | Direct map |

### research_sources

| Static Field | Supabase Column | Type | Notes |
|---|---|---|---|
| id | id | uuid | Generate new UUID; keep static id as `legacy_id` |
| title | title | text | Direct map |
| source | source | text | Direct map |
| score | score | integer | Direct map |
| lane | lane | text | Direct map |
| status | status | text | Direct map |
| type | type | text | Direct map |
| reason | reason | text | Direct map |
| nextAction | next_action | text | snake_case |
| convertOptions | convert_options | jsonb | Array stored as JSONB |
| createdAt | created_at | timestamptz | Direct map |

### monetization_opportunities

| Static Field | Supabase Column | Type | Notes |
|---|---|---|---|
| id | id | uuid | Generate new UUID; keep static id as `legacy_id` |
| name | name | text | Direct map |
| price | price | numeric | Direct map |
| audience | audience | text | Direct map |
| deliverables | deliverables | jsonb | Array stored as JSONB |
| stripeStatus | stripe_status | text | snake_case |
| status | status | text | Direct map |
| nextAction | next_action | text | snake_case |
| createdAt | created_at | timestamptz | Direct map |

### client_profiles

| Static Field | Supabase Column | Type | Notes |
|---|---|---|---|
| id | id | uuid | Generate new UUID; keep static id as `legacy_id` |
| name | name | text | Direct map |
| email | email | text | Direct map |
| status | status | text | Direct map |
| stage | stage | text | Direct map |
| onboardingReadiness | onboarding_readiness | integer | snake_case |
| paymentStatus | payment_status | text | snake_case |
| dashboardLiveFlag | dashboard_live_flag | boolean | snake_case |
| createdAt | created_at | timestamptz | Direct map |
| membershipTier | membership_tier | text | snake_case |
| advisorName | advisor_name | text | snake_case |
| readinessScores | readiness_scores | jsonb | Object stored as JSONB |
| documents | documents | jsonb | Object stored as JSONB |
| tasks | tasks | jsonb | Array stored as JSONB |
| messages | messages | jsonb | Array stored as JSONB |

---

## Dry-Run SQL Script

See `reports/static_to_supabase_seed_plan.json` for the machine-readable mapping.

**The following SQL is for review only. Execute only after Ray Review approval.**

```sql
-- DRY RUN: Do not execute until approved via Ray Review
-- Seed business_opportunities (26 rows)
-- INSERT INTO business_opportunities (id, title, category, score, revenue_range, confidence, status, reason, lane, next_action, convert_options, created_at)
-- VALUES
--   (gen_random_uuid(), 'Credit Readiness Assessment Service', 'credit_offer', 88, '$97–$297 per client', 'high', 'scored', 'Strong alignment with existing GoClear readiness framework...', 'credit_readiness', 'Map to the $97 offer structure...', '["offer","content","automation"]', '2026-06-28T10:00:00Z'),
--   ... (25 more rows)

-- Seed research_sources (50 rows)
-- Note: research_sources requires service role for INSERT (no anon policy)
-- Use Python script with SUPABASE_SERVICE_ROLE_KEY or create anon INSERT policy first

-- Seed monetization_opportunities (9 rows)
-- INSERT INTO monetization_opportunities (id, name, price, audience, deliverables, stripe_status, status, next_action, created_at)
-- VALUES ...

-- Seed client_profiles (1 row)
-- INSERT INTO client_profiles (id, name, email, status, stage, onboarding_readiness, payment_status, dashboard_live_flag, created_at, membership_tier, advisor_name, readiness_scores, documents, tasks, messages)
-- VALUES ...
```

---

## Execution Prerequisites

1. **Ray Review approval** for each table seed
2. **RLS policy check**: Confirm INSERT policy exists for authenticated users
3. **research_sources**: Either create anon INSERT policy or use service role script
4. **UUID generation**: Static IDs (biz-001, res-001, etc.) → new UUIDs; store originals as `legacy_id`
5. **Rollback plan**: Each seed should be reversible via `DELETE WHERE legacy_id LIKE 'biz-%'`

---

## Post-Seed Verification

After execution:
1. Open each section in the UI
2. SourceBanner should show "Live Supabase" instead of "Static snapshot"
3. Hermes source reasoning should confirm live data
4. Reload page — data should persist from Supabase
5. Check `countLive()` returns > 0 for each table

---

## Sections Still Static After Seed

Even after seeding, these sections remain static-only (no Supabase table mapped):
- **Trading Lab**: Inline data in NexusAdminUI — no separate component
- **System Health**: Reads from `src/data/systemHealthData.js` → `system_health` table exists but no anon INSERT
- **Automation**: Reads from inline data
- **Reports**: Reads from `src/data/reportRegistryData.js` → `nexus_events` table exists
- **Settings**: No settings data file
- **CLI**: No CLI registry data file
