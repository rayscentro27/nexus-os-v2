-- Nexus OS v2 — core schema. Supabase is the single source of truth (no file/report-as-state).
-- Apply via Supabase SQL editor or `supabase db push`.

create extension if not exists "pgcrypto";

-- 1. nexus_events — every meaningful action becomes a visible event (the ledger / proof log).
create table if not exists nexus_events (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  lane          text not null,                 -- communication | monetization | automation | social | trading | system
  source        text,
  action        text not null,
  status        text not null,                 -- success | failed | pending | info
  title         text,
  summary       text,
  payload       jsonb not null default '{}',
  visible_to_ray boolean not null default true,
  severity      text not null default 'info',  -- info | warning | critical
  correlation_id text,
  job_id        uuid,
  approval_id   uuid
);

-- 2. agent_jobs — one job runner tracks all automation work.
create table if not exists agent_jobs (
  id           uuid primary key default gen_random_uuid(),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  lane         text not null,
  job_type     text not null,
  status       text not null,                  -- queued | running | done | failed | skipped
  input        jsonb not null default '{}',
  output       jsonb not null default '{}',
  error        text,
  locked_by    text,
  locked_at    timestamptz,
  completed_at timestamptz
);

-- 3. approvals — approve/reject/revise/publish workflow.
create table if not exists approvals (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  lane        text not null,
  item_type   text not null,
  item_id     uuid,
  status      text not null,                   -- pending | approved | rejected | revise | published
  title       text,
  summary     text,
  payload     jsonb not null default '{}',
  approved_by text,
  decided_at  timestamptz
);

-- 4. social_accounts — connect existing accounts WITHOUT storing raw tokens in the DB/Git.
create table if not exists social_accounts (
  id              uuid primary key default gen_random_uuid(),
  created_at      timestamptz not null default now(),
  platform        text not null,
  account_name    text not null,
  account_id      text not null,
  username        text,
  status          text not null default 'unknown',
  token_env_key   text,                        -- name of the env var holding the token, never the token
  publish_enabled boolean not null default false,
  last_verified_at timestamptz,
  metadata        jsonb not null default '{}'
);

-- 5. social_posts — one social queue.
create table if not exists social_posts (
  id                  uuid primary key default gen_random_uuid(),
  created_at          timestamptz not null default now(),
  platform            text not null,
  account_id          uuid references social_accounts(id),
  content             text not null,
  media_url           text,
  status              text not null,           -- draft | needs_review | approved | published | rejected | revise
  score               numeric,
  reason              text,
  approval_id         uuid,
  published_url       text,
  published_external_id text,
  payload             jsonb not null default '{}'
);

-- 6. social_publish_receipts — safe publish receipts (no tokens).
create table if not exists social_publish_receipts (
  id             uuid primary key default gen_random_uuid(),
  created_at     timestamptz not null default now(),
  social_post_id uuid references social_posts(id),
  platform       text not null,
  status         text not null,
  external_id    text,
  published_url  text,
  error          text,
  receipt        jsonb not null default '{}'
);

-- 7. creative_assets — posts, videos, landing copy, newsletter, hooks, scripts.
create table if not exists creative_assets (
  id         uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  asset_type text not null,
  title      text,
  content    text,
  platform   text,
  offer      text,
  score      numeric,
  status     text not null default 'draft',
  payload    jsonb not null default '{}'
);

-- 8. business_opportunities — monetization/opportunity pipeline.
create table if not exists business_opportunities (
  id         uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  title      text not null,
  summary    text,
  score      numeric,
  status     text not null default 'new',
  plan       jsonb not null default '{}',
  payload    jsonb not null default '{}'
);

-- 9. trading_signals — research/signals only at first.
create table if not exists trading_signals (
  id         uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  market     text,
  instrument text,
  strategy   text,
  side       text,
  confidence numeric,
  entry      jsonb not null default '{}',
  risk       jsonb not null default '{}',
  status     text not null default 'new',
  payload    jsonb not null default '{}'
);

-- 10. demo_trades — Oanda demo/practice only (wired Day 6).
create table if not exists demo_trades (
  id               uuid primary key default gen_random_uuid(),
  created_at       timestamptz not null default now(),
  signal_id        uuid references trading_signals(id),
  broker           text not null default 'oanda',
  environment      text not null default 'demo',
  instrument       text,
  side             text,
  units            numeric,
  status           text not null,
  external_trade_id text,
  pnl              numeric,
  stop_loss        numeric,
  take_profit      numeric,
  payload          jsonb not null default '{}'
);

-- 11. telegram_messages — one guarded Telegram/War Room output record.
create table if not exists telegram_messages (
  id           uuid primary key default gen_random_uuid(),
  created_at   timestamptz not null default now(),
  purpose      text not null,
  chat_label   text,
  message_hash text not null,
  body_preview text,
  status       text not null,                  -- sent | suppressed | failed
  suppressed   boolean not null default false,
  payload      jsonb not null default '{}'
);

-- 12. system_health — dashboard health cards.
create table if not exists system_health (
  id         uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  component  text not null,
  status     text not null,                    -- ok | partial | failed | rebuild_needed | unknown
  summary    text,
  payload    jsonb not null default '{}'
);

-- 13. settings — flags/config visible in app.
create table if not exists settings (
  key        text primary key,
  value      jsonb not null,
  updated_at timestamptz not null default now()
);

-- ── Indexes ──
create index if not exists idx_nexus_events_created    on nexus_events (created_at desc);
create index if not exists idx_nexus_events_lane       on nexus_events (lane, created_at desc);
create index if not exists idx_agent_jobs_status       on agent_jobs (status, created_at desc);
create index if not exists idx_approvals_status        on approvals (status, created_at desc);
create index if not exists idx_social_posts_status     on social_posts (status, created_at desc);
create index if not exists idx_telegram_messages_hash  on telegram_messages (message_hash, created_at desc);

-- ── RLS ──
-- Enable RLS on every table. Day 1 policy: the service role (server/scripts) bypasses RLS;
-- the browser uses the ANON key and gets NO access until explicit read-only policies are
-- added. Never expose the service-role key to the frontend.
alter table nexus_events            enable row level security;
alter table agent_jobs              enable row level security;
alter table approvals               enable row level security;
alter table social_accounts         enable row level security;
alter table social_posts            enable row level security;
alter table social_publish_receipts enable row level security;
alter table creative_assets         enable row level security;
alter table business_opportunities  enable row level security;
alter table trading_signals         enable row level security;
alter table demo_trades             enable row level security;
alter table telegram_messages       enable row level security;
alter table system_health           enable row level security;
alter table settings                enable row level security;

-- NOTE: add explicit `create policy` statements in a later migration once the auth model is
-- decided (e.g. authenticated admin read). Until then, only the service role can read/write.
