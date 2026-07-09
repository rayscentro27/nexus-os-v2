-- Client Profile Intake Fields
-- Migration: 20260708120000
-- Safe: additive only, no DROP/TRUNCATE, no RLS changes, no policy weaken
-- Adds explicit columns for client-facing profile/business intake data

begin;

-- ── 1. Personal contact fields ──
alter table public.client_profiles add column if not exists legal_name text;
alter table public.client_profiles add column if not exists preferred_name text;
alter table public.client_profiles add column if not exists phone text;
alter table public.client_profiles add column if not exists mailing_address_line1 text;
alter table public.client_profiles add column if not exists mailing_address_line2 text;
alter table public.client_profiles add column if not exists city text;
alter table public.client_profiles add column if not exists state text;
alter table public.client_profiles add column if not exists postal_code text;

-- ── 2. Business identity fields ──
-- business_name stored in existing 'title' column; add alias column for clarity
alter table public.client_profiles add column if not exists business_name text;
alter table public.client_profiles add column if not exists entity_type text;
alter table public.client_profiles add column if not exists ein_status text;
alter table public.client_profiles add column if not exists industry text;
alter table public.client_profiles add column if not exists naics_code text;

-- ── 3. Business address fields ──
alter table public.client_profiles add column if not exists business_address_line1 text;
alter table public.client_profiles add column if not exists business_address_line2 text;
alter table public.client_profiles add column if not exists business_city text;
alter table public.client_profiles add column if not exists business_state text;
alter table public.client_profiles add column if not exists business_postal_code text;

-- ── 4. Funding readiness fields ──
alter table public.client_profiles add column if not exists time_in_business text;
alter table public.client_profiles add column if not exists monthly_revenue_range text;
alter table public.client_profiles add column if not exists funding_goal_range text;

-- ── 5. Index for profile completeness queries ──
create index if not exists idx_client_profiles_client_id
  on public.client_profiles (client_id);

commit;
