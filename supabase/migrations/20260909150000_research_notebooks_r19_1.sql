-- R19.1: first-class Admin research notebooks. Additive only.
create table if not exists public.research_notebooks (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid,
  title text not null,
  description text,
  owner_department text not null default 'RESEARCH',
  parent_goal_id text,
  status text not null default 'active',
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.research_sources add column if not exists notebook_id uuid;
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'research_sources_notebook_id_fkey') then
    alter table public.research_sources add constraint research_sources_notebook_id_fkey
      foreign key (notebook_id) references public.research_notebooks(id) on delete set null;
  end if;
end $$;

create index if not exists research_notebooks_tenant_updated_idx on public.research_notebooks(tenant_id, updated_at desc);
create index if not exists research_sources_notebook_idx on public.research_sources(notebook_id, created_at desc);
alter table public.research_notebooks enable row level security;
drop policy if exists research_notebooks_admin_select on public.research_notebooks;
create policy research_notebooks_admin_select on public.research_notebooks for select to authenticated using (public.nexus_is_active_admin());
drop policy if exists research_notebooks_admin_write on public.research_notebooks;
create policy research_notebooks_admin_write on public.research_notebooks for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin());
grant select, insert, update on public.research_notebooks to authenticated;

drop policy if exists research_sources_admin_insert on public.research_sources;
create policy research_sources_admin_insert on public.research_sources
  for insert to authenticated with check (public.nexus_is_active_admin());
