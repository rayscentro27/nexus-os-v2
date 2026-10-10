-- PULSE Trend & Market Intelligence V1.2. Additive; reuses Research's existing scheduler.
create table if not exists public.pulse_schedule_registry (
  job_id text primary key,
  cadence_seconds integer not null check (cadence_seconds > 0),
  enabled boolean not null default true,
  last_started_at timestamptz,
  last_success_at timestamptz,
  next_run_at timestamptz not null default now(),
  last_status text not null default 'IDLE_HEALTHY',
  last_result jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.pulse_provider_registry (
  provider_name text primary key,
  source_type text not null,
  free_or_paid text,
  auth_required boolean not null default false,
  automation_mode text,
  rate_limit jsonb not null default '{}'::jsonb,
  data_fields jsonb not null default '[]'::jsonb,
  current_status text not null default 'NOT_CONFIGURED',
  nexus_tested boolean not null default false,
  reliability text,
  commercial_use_notes text,
  terms_risk text,
  last_tested_at timestamptz,
  updated_at timestamptz not null default now()
);

create table if not exists public.pulse_notebook_templates (
  template_id text primary key,
  notebook_type text not null,
  owner_department text not null default 'PULSE',
  version text not null,
  prompt_body text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.pulse_trends (
  trend_id text primary key,
  source text,
  source_url text,
  platform text,
  topic text,
  keyword text,
  title text,
  creator text,
  detected_at timestamptz not null default now(),
  published_at timestamptz,
  current_views bigint,
  current_likes bigint,
  current_comments bigint,
  current_shares bigint,
  search_volume numeric,
  search_growth numeric,
  view_growth numeric,
  engagement_growth numeric,
  velocity numeric,
  acceleration numeric,
  cross_platform_count integer not null default 1,
  region text,
  language text,
  audience text,
  audience_intent text,
  pain_point text,
  desired_outcome text,
  emotional_driver text,
  content_format text,
  hook_pattern text,
  visual_pattern text,
  cta_pattern text,
  saturation numeric,
  competition numeric,
  trend_stage text,
  commercial_intent text,
  nexus_relevance text,
  confidence numeric,
  source_quality text not null default 'DISCOVERY_ONLY',
  trend_class text,
  expected_half_life text,
  urgency text,
  recheck_interval_seconds integer,
  component_scores jsonb not null default '{}'::jsonb,
  observed_data jsonb not null default '{}'::jsonb,
  derived_values jsonb not null default '{}'::jsonb,
  ai_inferences jsonb not null default '{}'::jsonb,
  commercial_matches jsonb not null default '[]'::jsonb,
  notebook_id uuid references public.research_notebooks(id) on delete set null,
  status text not null default 'DISCOVERED',
  route text,
  last_observed_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists pulse_trends_status_seen_idx on public.pulse_trends(status, last_observed_at desc);
create index if not exists pulse_trends_topic_idx on public.pulse_trends(topic, detected_at desc);

create table if not exists public.trend_history_bank (
  snapshot_id text primary key,
  trend_id text not null references public.pulse_trends(trend_id) on delete cascade,
  observed_at timestamptz not null default now(),
  views bigint,
  likes bigint,
  comments bigint,
  shares bigint,
  search_volume numeric,
  engagement numeric,
  velocity numeric,
  acceleration numeric,
  platform_count integer,
  saturation numeric,
  commercial_score numeric,
  opportunity_score numeric,
  status text,
  source_quality text,
  observed_data jsonb not null default '{}'::jsonb
);
create index if not exists trend_history_bank_trend_time_idx on public.trend_history_bank(trend_id, observed_at desc);

-- One compact, typed store backs the named shared intelligence banks.
create table if not exists public.pulse_shared_intelligence_bank (
  bank_name text not null check (bank_name in ('TREND_INTELLIGENCE_BANK','VIRAL_PATTERN_BANK','TREND_TO_REVENUE_BANK','AFFILIATE_OPPORTUNITY_BANK','PRODUCT_TREND_BANK','MERCHANDISE_OPPORTUNITY_BANK','CREATOR_PATTERN_BANK','TREND_CAMPAIGN_RESULT_BANK')),
  record_id text not null,
  trend_id text references public.pulse_trends(trend_id) on delete set null,
  evidence_state text not null default 'RESEARCH_REQUIRED',
  confidence numeric,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key(bank_name, record_id)
);

create table if not exists public.pulse_run_receipts (
  run_id text primary key,
  job_id text not null references public.pulse_schedule_registry(job_id),
  started_at timestamptz not null,
  completed_at timestamptz,
  status text not null,
  sources_discovered integer not null default 0,
  sources_processed integer not null default 0,
  trends_updated integer not null default 0,
  handoffs_created integer not null default 0,
  details jsonb not null default '{}'::jsonb
);

create table if not exists public.pulse_campaign_briefs (
  campaign_id text primary key,
  trend_id text not null references public.pulse_trends(trend_id),
  campaign_type text not null check (campaign_type in ('RAPID_CAMPAIGN','RAPID_MERCH_CAMPAIGN')),
  state text not null default 'READY_FOR_MARKETING_REVIEW',
  brief jsonb not null,
  publish_state text not null default 'NOT_PUBLISHED',
  ray_approval_required boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.pulse_handoffs (
  handoff_id text primary key,
  trend_id text not null references public.pulse_trends(trend_id),
  from_department text not null default 'PULSE',
  to_department text not null,
  case_id text,
  notebook_id uuid references public.research_notebooks(id) on delete set null,
  summary text not null,
  structured_data jsonb not null default '{}'::jsonb,
  what_was_completed jsonb not null default '[]'::jsonb,
  what_remains jsonb not null default '[]'::jsonb,
  recommendation text,
  action text,
  expected_output text,
  status text not null default 'CREATED' check (status in ('CREATED','CLAIMED','IN_PROGRESS','COMPLETED','BLOCKED','FAILED_RETRYABLE')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.pulse_printify_shops (
  shop_id text primary key,
  shop_title text,
  sales_channel text,
  store_status text,
  connection_status text,
  popup_store boolean,
  last_tested_at timestamptz not null default now(),
  safe_metadata jsonb not null default '{}'::jsonb
);

do $$ declare t text; begin
  foreach t in array array['pulse_schedule_registry','pulse_provider_registry','pulse_notebook_templates','pulse_trends','trend_history_bank','pulse_shared_intelligence_bank','pulse_run_receipts','pulse_campaign_briefs','pulse_handoffs','pulse_printify_shops'] loop
    execute format('alter table public.%I enable row level security',t);
    execute format('drop policy if exists %I on public.%I',t||'_admin_all',t);
    execute format('create policy %I on public.%I for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin())',t||'_admin_all',t);
    execute format('grant select, insert, update, delete on public.%I to authenticated',t);
  end loop;
end $$;

insert into public.pulse_schedule_registry(job_id,cadence_seconds,next_run_at,last_status)
values
 ('PULSE_FLASH_SCAN',7200,now(),'SCHEDULE_CONFIGURED'),
 ('PULSE_GENERAL_SCAN',14400,now()+interval '20 minutes','SCHEDULE_CONFIGURED'),
 ('PULSE_DAILY_DEEP_REVIEW',86400,now()+interval '40 minutes','SCHEDULE_CONFIGURED'),
 ('PULSE_DECAY_REVIEW',86400,now()+interval '60 minutes','SCHEDULE_CONFIGURED'),
 ('PULSE_COMMERCE_REFRESH',86400,now()+interval '80 minutes','SCHEDULE_CONFIGURED')
on conflict (job_id) do nothing;

insert into public.pulse_provider_registry(provider_name,source_type,free_or_paid,auth_required,automation_mode,data_fields,current_status,nexus_tested,commercial_use_notes,terms_risk)
values
 ('YOUTUBE','VIDEO_PLATFORM','MIXED',false,'EXISTING_NEXUS_COLLECTOR','["url","title","creator","published_at","views","likes","comments"]','AVAILABLE',true,'Direct public video metadata; preserve platform terms.','LOW'),
 ('GOOGLE_SEARCH_AUTOCOMPLETE','PUBLIC_SEARCH','FREE',false,'EXISTING_NEXUS_COLLECTOR','["related_queries"]','AVAILABLE',true,'Discovery only; query suggestions are not search-volume measurements.','LOW'),
 ('GOOGLE_TRENDS','SEARCH_TRENDS','FREE',false,'PUBLIC_RSS_OR_WEB','["trending_topics","region"]','NOT_TESTED',false,'Verify trend signals before commercial inference.','LOW'),
 ('GOOGLE_NEWS','NEWS','FREE',false,'RSS','["title","url","published_at"]','NOT_TESTED',false,'Use reputable and primary sources where available.','LOW'),
 ('TIKTOK_CREATIVE_CENTER','SOCIAL_TREND','FREE',true,'NOT_CONFIGURED','[]','NOT_CONFIGURED',false,'Public authenticated access not yet validated.','MEDIUM'),
 ('PRINTIFY_CATALOG','MERCH_CATALOG','FREE',false,'PUBLIC_API','["blueprint","provider","variant"]','AVAILABLE',true,'Catalog reads only; products and orders require approval.','LOW'),
 ('PRINTIFY_SHOPS','MERCH_STORE','FREE',true,'KEYCHAIN_TOKEN','["shop_id","title","sales_channel"]','BLOCKED_BY_AUTH',true,'Shop token rejected on authenticated read.','LOW'),
 ('VIEWSTATS','VIDEO_ANALYTICS','PAID_OR_LIMITED',true,'NOT_CONFIGURED','[]','NOT_CONFIGURED',false,'No account capability test run.','LOW'),
 ('SOCIAL_LISTENING','SOCIAL_SIGNAL','PAID',true,'NOT_CONFIGURED','[]','NOT_CONFIGURED',false,'Provider not configured.','MEDIUM'),
 ('AFFILIATE_CATALOGS','AFFILIATE','MIXED',true,'EXISTING_RESEARCH','["program_url","verification_status"]','PARTIAL',true,'Do not claim a program is active until official terms verify it.','MEDIUM'),
 ('TIKTOK_SHOP','COMMERCE','MIXED',true,'NOT_CONFIGURED','[]','NOT_CONFIGURED',false,'No account capability test run.','MEDIUM'),
 ('HACKER_NEWS','COMMUNITY_SIGNAL','FREE',false,'PUBLIC_API','["title","url","score"]','NOT_TESTED',false,'Technology/startup signals; not general demand evidence.','LOW'),
 ('BLUESKY','SOCIAL_SIGNAL','FREE',false,'PUBLIC_API','["post","engagement"]','NOT_TESTED',false,'Public signals only.','MEDIUM')
on conflict (provider_name) do update set current_status=excluded.current_status, data_fields=excluded.data_fields, updated_at=now();

insert into public.pulse_notebook_templates(template_id,notebook_type,owner_department,version,prompt_body)
values ('TREND_INTELLIGENCE_V1','TREND_INTELLIGENCE','PULSE','1.2',
'Analyze the trend cluster using current notebook sources. Keep observed facts separate from derived metrics and AI inferences. Identify what is trending, when it began, acceleration or decay, confirming platforms, strongest evidence, audience, engagement reasons, emotional driver, curiosity mechanism, repeated hooks, content and visual patterns, creator specificity, portability, platform dependence, saturation, half-life, products, affiliate programs, TikTok Shop, Printify matches, digital products, services, lead-generation opportunities, response speed, 24-hour and 72-hour actions, business-opportunity fit, rapid-campaign fit, rapid-merch fit, invalidating evidence, and next monitoring question. Do not invent demand, pricing, active affiliate programs, or commercial results. Output TREND_SUMMARY, EVIDENCE_SUMMARY, AUDIENCE_SUMMARY, VIRAL_MECHANISM, COMMERCIAL_MATCHES, AFFILIATE_MATCHES, MERCH_MATCHES, RISKS, RECOMMENDED_ROUTE, URGENCY, CONFIDENCE, NEXT_RECHECK.')
on conflict (template_id) do nothing;
