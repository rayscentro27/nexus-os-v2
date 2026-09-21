-- Marketing Distribution Layer V1. Additive, receipt-gated, and provider-neutral.
-- This reuses social_posts, approvals, agent_jobs, nexus_events, and the
-- department queue. It does not create a second scheduler or mutate CRM state.

create table if not exists public.marketing_social_content (
  social_content_id text primary key,
  campaign_id text not null,
  funnel_id text not null,
  objective_id text,
  channel text not null check (channel in ('facebook','instagram','linkedin','youtube','tiktok','x')),
  creative_asset_id text,
  content_type text not null,
  hook text,
  caption text not null,
  cta text,
  link text,
  hashtags jsonb not null default '[]'::jsonb,
  scheduled_at timestamptz,
  published_at timestamptz,
  provider_post_id text,
  status text not null check (status in ('DRAFT','AWAITING_APPROVAL','SCHEDULED','PUBLISHED','FAILED','HELD')),
  metrics jsonb not null default '{}'::jsonb,
  measurement_refs jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.marketing_email_messages (
  email_message_id text primary key,
  campaign_id text not null,
  funnel_id text not null,
  lead_id text,
  recipient text not null,
  segment text,
  message_type text not null check (message_type in ('TEST','TRANSACTIONAL','MARKETING','NURTURE','BULK')),
  subject text not null,
  body_ref text,
  cta text,
  tracking_id text not null,
  send_status text not null check (send_status in ('DRAFT','QUEUED','SENT','FAILED','HELD')),
  provider text,
  provider_message_id text,
  delivery_status text not null default 'UNKNOWN',
  open_status text not null default 'UNKNOWN',
  click_status text not null default 'UNKNOWN',
  bounce_status text not null default 'UNKNOWN',
  unsubscribe_status text not null default 'UNKNOWN',
  created_at timestamptz not null default now(),
  sent_at timestamptz
);

create table if not exists public.marketing_distribution_records (
  distribution_id text primary key,
  campaign_id text not null,
  funnel_id text not null,
  channel text not null,
  content_id text not null,
  provider text,
  status text not null,
  scheduled_at timestamptz,
  sent_or_published_at timestamptz,
  provider_object_id text,
  metrics_refs jsonb not null default '[]'::jsonb,
  cost numeric not null default 0,
  failure_reason text,
  retry_state jsonb not null default '{}'::jsonb,
  receipt_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (cost >= 0)
);

create table if not exists public.marketing_distribution_events (
  event_id text primary key,
  distribution_id text not null references public.marketing_distribution_records(distribution_id) on delete cascade,
  event_type text not null,
  provider_event_id text,
  occurred_at timestamptz not null default now(),
  payload jsonb not null default '{}'::jsonb
);

create table if not exists public.marketing_attribution_refs (
  distribution_id text primary key references public.marketing_distribution_records(distribution_id) on delete cascade,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  utm_content text,
  creative_variant text,
  destination_url text,
  created_at timestamptz not null default now()
);

create table if not exists public.marketing_nurture_sequences (
  sequence_id text primary key,
  funnel_id text not null,
  name text not null,
  trigger_definition jsonb not null default '{}'::jsonb,
  steps jsonb not null default '[]'::jsonb,
  stop_condition jsonb not null default '{}'::jsonb,
  success_event text,
  status text not null default 'DRAFT' check (status in ('DRAFT','APPROVED','ACTIVE','HELD')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists marketing_social_content_campaign_idx on public.marketing_social_content(campaign_id, status, updated_at desc);
create index if not exists marketing_distribution_funnel_idx on public.marketing_distribution_records(funnel_id, status, updated_at desc);
create index if not exists marketing_email_tracking_idx on public.marketing_email_messages(tracking_id);
create index if not exists marketing_distribution_events_idx on public.marketing_distribution_events(distribution_id, occurred_at desc);

do $$
declare t text;
begin
  foreach t in array array['marketing_social_content','marketing_email_messages','marketing_distribution_records','marketing_distribution_events','marketing_attribution_refs','marketing_nurture_sequences'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', 'admin_read_' || t, t);
    execute format('create policy %I on public.%I for select to authenticated using (exists (select 1 from public.admin_users a where a.id = auth.uid() and a.active = true))', 'admin_read_' || t, t);
  end loop;
end $$;

grant select on public.marketing_social_content, public.marketing_email_messages,
  public.marketing_distribution_records, public.marketing_distribution_events,
  public.marketing_attribution_refs, public.marketing_nurture_sequences to authenticated;
