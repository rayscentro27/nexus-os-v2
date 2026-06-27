-- Nexus OS v2 — Client Workflow Engine (GoClear / Apex). ADDITIVE ONLY.
-- Durable client-domain tables for the signup -> funding-ready workflow. Admin-only RLS reusing
-- the existing admin_users gate (same pattern as task_requests / core tables). No anon/public
-- policies. No secrets, no SmartCredit passwords, no scraped data stored here.
--
-- Sensitivity model (mirrors task_requests): rows here are credit_sensitive / funding_sensitive
-- and must never be exposed client-facing until Ray approves the plan.

create extension if not exists pgcrypto;

-- A. client_profiles — one row per client workflow.
create table if not exists client_profiles (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid references workspaces(id),
  client_label text not null,
  current_stage text not null default 'signup_started',
  next_required_action text,
  due_at timestamptz,
  days_stuck integer not null default 0,
  progress_percentage integer not null default 0,
  funding_readiness_impact integer not null default 0,
  revenue_risk_level text not null default 'low',           -- low | medium | high | critical
  ray_review_status text not null default 'not_needed',     -- not_needed | pending_review | approved | changes_requested
  client_visible_status text,
  selected_credit_report_source text,                       -- smartcredit | annualcreditreport | manual_upload | other
  source_selected_at timestamptz,
  affiliate_partner_id uuid references partner_offers(id),
  affiliate_url text,
  affiliate_disclosure_accepted boolean not null default false,
  client_consent_accepted boolean not null default false,
  score_available boolean not null default false,
  score_source text not null default 'unavailable',         -- smartcredit | manual_entry | imported_report | unavailable
  report_upload_status text not null default 'not_started',
  report_import_status text not null default 'not_started',
  sensitivity text not null default 'credit_sensitive',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- B. client_workflow_stage_history — append-only stage transitions.
create table if not exists client_workflow_stage_history (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references client_profiles(id) on delete cascade,
  workspace_id uuid references workspaces(id),
  from_stage text,
  to_stage text not null,
  note text,
  changed_by text not null default 'system',
  created_at timestamptz not null default now()
);

-- C. credit_score_history — score tracking over time (manual or imported; never scraped).
create table if not exists credit_score_history (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references client_profiles(id) on delete cascade,
  workspace_id uuid references workspaces(id),
  bureau text not null default 'unknown',                   -- equifax | experian | transunion | unknown
  score integer,
  score_model text,
  score_source text not null default 'manual_entry',        -- smartcredit | manual_entry | imported_report | unavailable
  reported_at timestamptz not null default now(),
  imported_from text,
  notes text,
  sensitivity text not null default 'credit_sensitive',
  created_at timestamptz not null default now()
);

-- D. business_setup_items — per-client setup item state (partner vs DIY).
create table if not exists business_setup_items (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references client_profiles(id) on delete cascade,
  workspace_id uuid references workspaces(id),
  setup_item_key text not null,
  setup_item_name text not null,
  required_for_bankability boolean not null default false,
  recommended_partner_name text,
  partner_affiliate_url text,
  partner_disclosure_text text,
  diy_official_option_name text,
  diy_official_url text,
  diy_instruction_text text,
  client_selected_path text not null default 'undecided',   -- partner | diy | already_completed | not_applicable | undecided
  completion_status text not null default 'not_started',    -- not_started | in_progress | completed | verified
  proof_required boolean not null default false,
  proof_file_path text,
  verified_status text not null default 'unverified',
  bankability_score_impact integer not null default 0,
  funding_readiness_score_impact integer not null default 0,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (client_id, setup_item_key)
);

-- E. credit_letter_packets — letter drafts (approval-gated; never auto-mailed).
create table if not exists credit_letter_packets (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references client_profiles(id) on delete cascade,
  workspace_id uuid references workspaces(id),
  letter_type text not null,                                -- bureau_dispute | creditor_dispute | ...
  recipient_type text not null default 'bureau',            -- bureau | creditor | collector | lender | other
  recipient_name text,
  recipient_address text,
  letter_body text,
  attachments_needed text,
  status text not null default 'draft',
  approval_status text not null default 'draft',            -- draft | pending_approval | approved | changes_requested
  approved_by text,
  approved_at timestamptz,
  sensitivity text not null default 'credit_sensitive',
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- F. client_mailings — mailing tracking (DocuPost connector shell / USPS DIY). No auto-send.
create table if not exists client_mailings (
  id uuid primary key default gen_random_uuid(),
  letter_packet_id uuid references credit_letter_packets(id) on delete cascade,
  client_id uuid references client_profiles(id) on delete cascade,
  workspace_id uuid references workspaces(id),
  mailing_method text not null default 'usps_certified',    -- docupost | usps_certified | manual_other
  partner_affiliate_url text,
  mailing_status text not null default 'not_started',
  postage_cost numeric,
  tracking_number text,
  certified_mail_receipt_file_path text,
  return_receipt_file_path text,
  docupost_tracking_id text,
  docupost_tracking_url text,
  mailed_at timestamptz,
  expected_response_deadline timestamptz,
  follow_up_due_at timestamptz,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- G. client_reminders — stuck-client / progress reminders (drafts only; no auto external send).
create table if not exists client_reminders (
  id uuid primary key default gen_random_uuid(),
  client_id uuid references client_profiles(id) on delete cascade,
  workspace_id uuid references workspaces(id),
  workflow_area text not null,                              -- credit | business | funding
  task_key text not null,
  task_title text not null,
  task_description text,
  due_at timestamptz,
  completed_at timestamptz,
  completion_proof_path text,
  reminder_status text not null default 'pending',          -- pending | sent_internal | completed | escalated | snoozed
  reminder_count integer not null default 0,
  last_reminder_at timestamptz,
  next_reminder_at timestamptz,
  escalation_status text not null default 'none',           -- none | hermes | ray
  revenue_risk_level text not null default 'low',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_client_profiles_stage on client_profiles (current_stage, updated_at desc);
create index if not exists idx_client_profiles_risk on client_profiles (revenue_risk_level, days_stuck desc);
create index if not exists idx_setup_items_client on business_setup_items (client_id, setup_item_key);
create index if not exists idx_letters_client on credit_letter_packets (client_id, approval_status);
create index if not exists idx_mailings_client on client_mailings (client_id, mailing_status);
create index if not exists idx_reminders_client on client_reminders (client_id, reminder_status);
create index if not exists idx_score_history_client on credit_score_history (client_id, reported_at desc);

-- RLS: admin-only read/insert/update on every table (same pattern as task_requests). No anon/public.
do $$
declare t text;
begin
  foreach t in array array[
    'client_profiles','client_workflow_stage_history','credit_score_history',
    'business_setup_items','credit_letter_packets','client_mailings','client_reminders'
  ] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists %I on %I', 'admin read ' || t, t);
    execute format(
      'create policy %I on %I for select to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin read ' || t, t);
    execute format('drop policy if exists %I on %I', 'admin insert ' || t, t);
    execute format(
      'create policy %I on %I for insert to authenticated with check ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin insert ' || t, t);
    execute format('drop policy if exists %I on %I', 'admin update ' || t, t);
    execute format(
      'create policy %I on %I for update to authenticated using ('
      || 'exists (select 1 from admin_users a where a.id = auth.uid() and a.active = true))',
      'admin update ' || t, t);
  end loop;
end $$;
