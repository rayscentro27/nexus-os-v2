# Nexus High-Risk Guard Verification

- generated_at: 2026-06-26T23:31:44.747714+00:00
- ok: True
- blocked: 19/19

## Guards
- blocked · Live trading (live_trade) — Real money at risk; irreversible market actions.
- blocked · Broker order execution (broker_order) — Direct broker orders move real funds.
- blocked · Funded account actions (funded_account_execution) — Funded accounts can lose real capital.
- blocked · Raw auto_executor exposure (auto_executor_exposure) — Raw executor could run arbitrary risky actions.
- blocked · Payment charge (payment_charge) — Spends real money / charges customers.
- blocked · Payment refund (payment_refund) — Moves real money out.
- blocked · Ad spend activation (ad_spend_activation) — Spends real money on ads.
- blocked · Production deploy (production_deploy) — Can break the live system.
- blocked · RLS weakening (rls_weaken) — Could expose tenant/customer data.
- blocked · Destructive DB write (destructive_db_write) — Data loss / corruption risk.
- blocked · Secret printing (secret_print) — Leaks credentials/tokens/cookies.
- blocked · .env commit (env_commit) — Leaks secrets into git history.
- blocked · Broad scraping (broad_scrape) — Legal/ToS risk and resource abuse.
- blocked · YouTube media download (youtube_media_download) — Copyright/ToS risk and heavy I/O.
- blocked · External AI on sensitive data (external_ai_sensitive_data) — Leaks private/customer/credit data.
- blocked · Bulk send (bulk_send) — Mass outbound can spam.
- blocked · Spam automation (spam_automation) — Abusive automated outreach.
- blocked · Client data exposure (client_data_exposure) — Exposes private client data externally.
- blocked · Tenant isolation bypass (tenant_isolation_bypass) — Cross-tenant data leakage.
