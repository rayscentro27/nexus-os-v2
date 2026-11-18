-- Isolated shadow-only Research Room state; never used by production Research.
create table if not exists public.research_room_cases (
    case_id text primary key,
    root_objective text not null,
    status text not null check (status in ('OPEN', 'WORKING', 'SYNTHESIZING', 'HANDED_OFF', 'COMPLETE')),
    shadow_mode boolean not null default true check (shadow_mode is true),
    state jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.research_room_cases enable row level security;
revoke all on public.research_room_cases from anon, authenticated;
grant select, insert, update on public.research_room_cases to service_role;
