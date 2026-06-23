-- Nexus OS v2 — Day 4 Creative Studio asset engine. ADDITIVE ONLY (no destructive changes).
-- Adds link + structured-content columns to creative_assets so generated assets connect to a
-- campaign/brief/workspace and carry hook/cta/body/approval. RLS stays as-is: creative_assets
-- already has the admin SELECT policy (0002); scripts write via the service role (bypasses RLS).
-- No anon/public policies.

alter table creative_assets add column if not exists campaign_id  uuid references creative_campaigns(id);
alter table creative_assets add column if not exists brief_id     uuid references creative_briefs(id);
alter table creative_assets add column if not exists workspace_id uuid references workspaces(id);
alter table creative_assets add column if not exists hook         text;
alter table creative_assets add column if not exists body         text;
alter table creative_assets add column if not exists cta          text;
alter table creative_assets add column if not exists approval_id  uuid references approvals(id);
alter table creative_assets add column if not exists score_id     uuid references creative_scores(id);

create index if not exists idx_creative_assets_campaign on creative_assets (campaign_id, created_at desc);
create index if not exists idx_creative_assets_status   on creative_assets (status, created_at desc);
