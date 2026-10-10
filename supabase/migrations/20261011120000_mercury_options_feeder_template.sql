create table if not exists public.trading_notebook_templates (
  template_type text primary key,
  owner_department text not null,
  manager_department text not null,
  master_prompt text not null,
  version text not null,
  status text not null default 'ACTIVE',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.trading_notebook_templates enable row level security;
drop policy if exists trading_notebook_templates_admin_all on public.trading_notebook_templates;
create policy trading_notebook_templates_admin_all on public.trading_notebook_templates for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
notify pgrst, 'reload schema';
