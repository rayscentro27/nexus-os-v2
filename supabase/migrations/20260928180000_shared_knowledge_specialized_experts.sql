-- Additive shared-knowledge and specialist-expert architecture.
alter table public.research_findings add column if not exists finding_id text;
alter table public.research_findings add column if not exists research_job_id text;
alter table public.research_findings add column if not exists source_type text;
alter table public.research_findings add column if not exists source_name text;
alter table public.research_findings add column if not exists source_url text;
alter table public.research_findings add column if not exists source_date timestamptz;
alter table public.research_findings add column if not exists source_author text;
alter table public.research_findings add column if not exists source_channel text;
alter table public.research_findings add column if not exists raw_artifact_reference text;
alter table public.research_findings add column if not exists transcript_reference text;
alter table public.research_findings add column if not exists content_hash text;
alter table public.research_findings add column if not exists research_mode text;
alter table public.research_findings add column if not exists requested_by text;
alter table public.research_findings add column if not exists parent_finding_id text;
alter table public.research_findings add column if not exists parent_department_request_id text;
alter table public.research_findings add column if not exists summary text;
alter table public.research_findings add column if not exists claims jsonb not null default '[]'::jsonb;
alter table public.research_findings add column if not exists evidence jsonb not null default '[]'::jsonb;
alter table public.research_findings add column if not exists unknowns jsonb not null default '[]'::jsonb;
alter table public.research_findings add column if not exists contradictions jsonb not null default '[]'::jsonb;
alter table public.research_findings add column if not exists followup_questions jsonb not null default '[]'::jsonb;
alter table public.research_findings add column if not exists primary_subject text;
alter table public.research_findings add column if not exists secondary_subjects jsonb not null default '[]'::jsonb;
alter table public.research_findings add column if not exists tags jsonb not null default '[]'::jsonb;
alter table public.research_findings add column if not exists entities jsonb not null default '[]'::jsonb;
alter table public.research_findings add column if not exists classification_status text not null default 'UNCLASSIFIED';
alter table public.research_findings add column if not exists classification_confidence text not null default 'LOW';
alter table public.research_findings add column if not exists relevant_departments jsonb not null default '[]'::jsonb;
alter table public.research_findings add column if not exists alpha_review_id text;
alter table public.research_findings add column if not exists alpha_opinion text;
alter table public.research_findings add column if not exists scam_status text not null default 'UNKNOWN';
create unique index if not exists research_findings_finding_id_uidx on public.research_findings(finding_id) where finding_id is not null;
create table if not exists public.nexus_expert_registry (expert_id text primary key,name text not null,domain text not null,role text not null,responsibilities jsonb not null default '[]'::jsonb,blocked_actions jsonb not null default '[]'::jsonb,active boolean not null default true,created_at timestamptz not null default now(),updated_at timestamptz not null default now());
create table if not exists public.department_information_items (information_item_id text primary key,finding_id text not null,expert_id text not null,why_relevant text,priority integer not null default 50, status text not null default 'PENDING',created_at timestamptz not null default now(),claimed_at timestamptz,processed_at timestamptz,expert_assessment_id text,source_lineage jsonb not null default '{}'::jsonb,unique(finding_id,expert_id));
create table if not exists public.department_assessments (assessment_id text primary key,finding_id text not null,expert_id text not null,relevant_to_domain text not null,what_is_new text,what_changed text,confirms text,contradicts text,uncertainty jsonb not null default '[]'::jsonb,disposition text not null,reason text,evidence jsonb not null default '[]'::jsonb,next_action text,created_at timestamptz not null default now());
create table if not exists public.department_knowledge (knowledge_id text primary key,finding_id text not null,expert_id text not null,subject text,lesson text not null,source_lineage jsonb not null default '{}',assessment_lineage jsonb not null default '{}',result_lineage jsonb not null default '{}',created_at timestamptz not null default now());
create table if not exists public.department_lessons (lesson_id text primary key,finding_id text not null,expert_id text not null,success_failure text not null,lesson text not null,next_decision_rule text,result_lineage jsonb not null default '{}',created_at timestamptz not null default now());
create table if not exists public.department_open_questions (question_id text primary key,finding_id text not null,expert_id text not null,question text not null,status text not null default 'OPEN',created_at timestamptz not null default now());
create table if not exists public.department_research_requests (request_id text primary key,expert_id text not null,assessment_id text,parent_finding_id text,research_question text not null,required_evidence jsonb not null default '[]'::jsonb,preferred_source_types jsonb not null default '[]'::jsonb,status text not null default 'QUEUED',created_at timestamptz not null default now());
create index if not exists department_information_pending_idx on public.department_information_items(expert_id,status,created_at);
create index if not exists department_assessment_finding_idx on public.department_assessments(finding_id,created_at desc);
do $$ declare t text; begin foreach t in array array['nexus_expert_registry','department_information_items','department_assessments','department_knowledge','department_lessons','department_open_questions','department_research_requests'] loop execute format('alter table public.%I enable row level security',t); execute format('drop policy if exists %I_admin_all on public.%I',t,t); execute format('create policy %I_admin_all on public.%I for all to authenticated using (public.nexus_is_active_admin()) with check (public.nexus_is_active_admin())',t,t); end loop; end $$;
grant select,insert,update on public.nexus_expert_registry to authenticated;
grant select,insert,update on public.department_information_items to authenticated;
grant select,insert,update on public.department_assessments to authenticated;
grant select,insert,update on public.department_knowledge to authenticated;
grant select,insert,update on public.department_lessons to authenticated;
grant select,insert,update on public.department_open_questions to authenticated;
grant select,insert,update on public.department_research_requests to authenticated;

insert into public.nexus_expert_registry (expert_id,name,domain,role,responsibilities,blocked_actions)
values
 ('CLYDE_CREDIT','Clyde','CREDIT','specialized_domain_expert','["consumer credit","credit reports","utilization","inquiries","derogatories","credit readiness","credit repair workflow knowledge","disputes","credit education"]'::jsonb,'["send disputes","contact bureaus","unauthorized client actions"]'::jsonb),
 ('GRANT_FUNDING','Grant','FUNDING','specialized_domain_expert','["business funding","lenders","underwriting","business credit products","SBA","lines of credit","grants","funding readiness","lender/product matching"]'::jsonb,'["submit funding applications","client commitments"]'::jsonb),
 ('ATLAS_OPPORTUNITY','Atlas','BUSINESS_OPPORTUNITY','specialized_domain_expert','["business models","monetization","affiliate opportunities","consulting","education offers","product opportunities","market validation","experiments","revenue outcomes"]'::jsonb,'[]'::jsonb),
 ('MERCURY_TRADING','Mercury','TRADING','specialized_domain_expert','["trading strategies","forex","indicators","backtests","strategy rules","risk","drawdown","repainting","overfitting","paper/demo testing"]'::jsonb,'["funded/live trades"]'::jsonb),
 ('FORGE_SYSTEMS','Forge','SYSTEMS','specialized_domain_expert','["repositories","software tools","AI models","infrastructure","installation","compatibility","deployment","performance","technical alternatives","sandbox evaluation"]'::jsonb,'["unsafe production mutation"]'::jsonb),
 ('MIRA_MARKETING','Mira','MARKETING','specialized_domain_expert','["customer demand","audience understanding","messaging","funnels","acquisition","campaign testing","conversion learning","content performance","lead-generation intelligence"]'::jsonb,'["unapproved publishing or spend"]'::jsonb),
 ('LEDGER_FINANCE','Ledger','FINANCE','specialized_domain_expert','["cost","budgets","recurring spend","affordability","financial constraints","ROI","tool/infrastructure cost evaluation"]'::jsonb,'[]'::jsonb),
 ('SCOUT_INTELLIGENCE','Scout','SEO_CUSTOMER_INTELLIGENCE','specialized_domain_expert','["SEO research","search-demand research","keyword movement","customer questions","customer complaints","customer needs","search intent","topic discovery","last-30-day demand signals"]'::jsonb,'[]'::jsonb)
on conflict (expert_id) do update set name=excluded.name,domain=excluded.domain,role=excluded.role,responsibilities=excluded.responsibilities,blocked_actions=excluded.blocked_actions,updated_at=now();
