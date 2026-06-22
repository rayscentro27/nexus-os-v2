-- Seed known social accounts. NO TOKENS — only public account IDs + the env var NAME that
-- holds the token at runtime. Tokens live in .env / deployment secret stores, never here.
-- Idempotent: safe to re-run.

insert into social_accounts (platform, account_name, account_id, username, status, token_env_key, publish_enabled)
select 'facebook', 'Clear Credentials', '131069194210954', null, 'unknown', 'META_PAGE_ACCESS_TOKEN', false
where not exists (select 1 from social_accounts where platform = 'facebook' and account_id = '131069194210954');

insert into social_accounts (platform, account_name, account_id, username, status, token_env_key, publish_enabled)
select 'instagram', 'GoClearOnline', '17841480265043148', 'goclearonline', 'unknown', 'META_PAGE_ACCESS_TOKEN', false
where not exists (select 1 from social_accounts where platform = 'instagram' and account_id = '17841480265043148');
