-- NEXUS_COMMERCE_CONVERSION_AND_MEASUREMENT_R1 (owner-approved 2026-11-15)
-- Additive only. First-party funnel storage for ONE pilot storefront.
-- Anonymous storefront visitors may INSERT leads/events for the allow-listed pilot only;
-- they can never SELECT/UPDATE/DELETE. Orders are written only by Nexus (service role)
-- after server-side verification with Stripe.

create table if not exists public.commerce_leads (
  lead_id uuid primary key default gen_random_uuid(),
  project_id text not null,
  venture_id text not null,
  opportunity_id text not null,
  product_id text not null,
  email text not null check (char_length(email) <= 254 and email ~* '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]{2,}$'),
  email_normalized text generated always as (lower(btrim(email))) stored,
  first_name text check (first_name is null or char_length(first_name) <= 60),
  session_id text check (session_id is null or char_length(session_id) <= 64),
  source text check (source is null or char_length(source) <= 64),
  campaign text check (campaign is null or char_length(campaign) <= 96),
  content_variant text check (content_variant is null or char_length(content_variant) <= 64),
  utm_source text check (utm_source is null or char_length(utm_source) <= 64),
  utm_medium text check (utm_medium is null or char_length(utm_medium) <= 64),
  utm_campaign text check (utm_campaign is null or char_length(utm_campaign) <= 96),
  utm_content text check (utm_content is null or char_length(utm_content) <= 64),
  is_test boolean not null default false,
  created_at timestamptz not null default now(),
  unique (project_id, email_normalized)
);

create table if not exists public.commerce_events (
  event_id uuid primary key default gen_random_uuid(),
  event_type text not null check (event_type in ('PAGE_VIEW','CTA_CLICK','INTEREST_FORM_STARTED','INTEREST_FORM_SUBMITTED',
                                                 'CHECKOUT_CLICK','CHECKOUT_STARTED','PURCHASE_COMPLETED')),
  project_id text not null,
  venture_id text not null,
  opportunity_id text not null,
  product_id text not null,
  session_id text not null check (char_length(session_id) <= 64),
  source text check (source is null or char_length(source) <= 64),
  campaign text check (campaign is null or char_length(campaign) <= 96),
  content_variant text check (content_variant is null or char_length(content_variant) <= 64),
  utm_source text check (utm_source is null or char_length(utm_source) <= 64),
  utm_medium text check (utm_medium is null or char_length(utm_medium) <= 64),
  utm_campaign text check (utm_campaign is null or char_length(utm_campaign) <= 96),
  utm_content text check (utm_content is null or char_length(utm_content) <= 64),
  page_path text check (page_path is null or char_length(page_path) <= 200),
  detail jsonb not null default '{}'::jsonb check (pg_column_size(detail) <= 2048),
  verified boolean not null default false,   -- true only for Nexus server-verified events
  is_test boolean not null default false,
  client_ts timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists commerce_events_project_type_idx on public.commerce_events (project_id, event_type, created_at);

create table if not exists public.commerce_orders (
  order_id uuid primary key default gen_random_uuid(),
  project_id text not null,
  venture_id text not null,
  opportunity_id text not null,
  product_id text not null,
  provider text not null check (provider in ('STRIPE')),
  mode text not null check (mode in ('TEST','LIVE')),
  provider_session_id text not null unique,
  payment_status text not null,
  amount_total_cents integer not null check (amount_total_cents >= 0),
  currency text not null,
  session_id text,
  utm_source text, utm_medium text, utm_campaign text, utm_content text, content_variant text,
  provider_created_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.commerce_leads enable row level security;
alter table public.commerce_events enable row level security;
alter table public.commerce_orders enable row level security;

revoke all on public.commerce_leads, public.commerce_events, public.commerce_orders from anon, authenticated;
grant insert (project_id, venture_id, opportunity_id, product_id, email, first_name, session_id, source, campaign, content_variant,
              utm_source, utm_medium, utm_campaign, utm_content) on public.commerce_leads to anon;
grant insert (event_type, project_id, venture_id, opportunity_id, product_id, session_id, source, campaign, content_variant,
              utm_source, utm_medium, utm_campaign, utm_content, page_path, detail, client_ts) on public.commerce_events to anon;

drop policy if exists commerce_leads_pilot_insert on public.commerce_leads;
create policy commerce_leads_pilot_insert on public.commerce_leads for insert to anon
  with check (project_id = 'proj_98ef515bccee4b58' and venture_id = 'vnt_holiday_commerce_pilot_2026'
              and opportunity_id = 'opp_holiday_ceramic_mug_2026' and product_id = 'prod_stoneware_mug_14oz' and is_test = false);

drop policy if exists commerce_events_pilot_insert on public.commerce_events;
create policy commerce_events_pilot_insert on public.commerce_events for insert to anon
  with check (project_id = 'proj_98ef515bccee4b58' and venture_id = 'vnt_holiday_commerce_pilot_2026'
              and opportunity_id = 'opp_holiday_ceramic_mug_2026' and product_id = 'prod_stoneware_mug_14oz'
              and verified = false and is_test = false);
-- commerce_orders: no anon/authenticated policy (service role only).
