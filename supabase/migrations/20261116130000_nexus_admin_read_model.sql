-- NEXUS_FINAL_OVERNIGHT_COMPLETION_R1: Admin Center read model (additive).
-- Written only by the Mac publisher with the service role; read only by the
-- admin-guarded Netlify function (service role). No anon/authenticated access.
create table if not exists public.nexus_admin_read_model (
  area text primary key check (char_length(area) <= 64),
  payload jsonb not null,
  generated_at timestamptz not null,
  updated_at timestamptz not null default now()
);
alter table public.nexus_admin_read_model enable row level security;
revoke all on public.nexus_admin_read_model from anon, authenticated;
