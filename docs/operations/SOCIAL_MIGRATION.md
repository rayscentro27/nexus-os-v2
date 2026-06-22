# Social Migration

Reuse the existing, proven accounts — migrate the **token via env only**, never the repo/DB.

## Accounts (seeded in `supabase/seed/0001_social_accounts.sql`)
- **Facebook Page:** Clear Credentials — `131069194210954`
- **Instagram:** @goclearonline — `17841480265043148`

Both are seeded with `publish_enabled = false` and `token_env_key = META_PAGE_ACCESS_TOKEN`.
The row stores the **name** of the env var that holds the token — never the token itself.

## Token handling
- The Facebook Page token lives only in `.env` (`META_PAGE_ACCESS_TOKEN`) and deployment
  secret stores.
- Use a **long-lived / non-expiring Page token** (exchange a long-lived USER token →
  `/me/accounts` → Page token). The old Nexus `scripts/facebook_token_status.py --exchange`
  is the reference; it will be ported in a later day.
- No tokens in Supabase during Day 1 (Supabase Vault is an option later if we want DB-managed
  secrets, used intentionally — not Day 1).

## Day 3 plan
- Port the Facebook publisher logic from old Nexus (`content_employee/publisher.py` idea):
  Graph `/{page_id}/feed` for text, container flow for media.
- Publishing path: queue item → `needs_review` → `approved` → dry-run → publish → receipt
  (`social_publish_receipts`, token-free) → `nexus_events`.
- Set `publish_enabled = true` only after a verified token + an explicit approval.

## Instagram
Deferred until a media/container pipeline exists (render → host public URL → create container
→ poll → publish). Keep `publish_enabled = false` until then.
