# Nexus — UI Data Connection Audit

- generated_at: 2026-06-24
- deployed app: https://nexusv20.netlify.app (Supabase project iqjwgpnujbeoyaeuwehj — confirmed in the deployed bundle)
- build: PASS · nexus:watch: PASS · nothing published/sent/traded · no scheduler

---

## What was broken
The Approvals tab (and effectively every admin data tab) showed the empty state
*"No approvals yet…"* even though approval `13eafcab` (and 11 others) exist in Supabase.

## Root cause — expired/unauthenticated session, not mock data
- The Approvals UI **is wired to Supabase** (anon client), reading the **`approvals`** table via
  `listTable('approvals', { limit: 30 })` → `supabase.from('approvals').select('*')`. Not mock.
- `approvals` is **admin-only RLS**: `using (exists (select 1 from admin_users a where a.id =
  auth.uid() and a.active = true))`.
- Admin mapping is **correct**: Ray's auth user id `81fbb840-67cf-401f-8f98-3a73652d5193`
  == `admin_users.id` (active, email-confirmed). So an authenticated admin session *should* see
  the rows.
- **The bug:** the Supabase client was created with `auth: { persistSession: false }` (and no
  auto-refresh). The access token (~1h TTL) is not persisted or refreshed, so after sign-in expires
  or on reload the client queries **unauthenticated**. Admin-only RLS then returns **0 rows with no
  error**, and `listTable` swallows that into an empty array → the generic empty message.
- Verified the deployed bundle points at the same project (`iqjwgpnujbeoyaeuwehj`) and Ray signed in
  there today (19:26Z) — so it is **not** an env/project/tenant mismatch and **not** a wrong query.

### Diagnosis answers
1. Wired to Supabase? **Yes** (anon client), not mock.
2. Table read? **`approvals`**.
3. Query/filter? `select * order created_at desc limit 30` (no tenant/user filter).
4. Why `13eafcab` didn't appear? Admin-only RLS returned 0 rows because the query ran without a
   valid authenticated JWT (session not persisted/refreshed).
5. Category? **Auth/session handling bug** (client config) — not env, not RLS misconfig, not tenant,
   not query, not mock.
6. Are other tabs mock? **No** — they are all live Supabase reads, all gated by the same admin RLS,
   so all were silently empty under the expired session.
7. Live vs placeholder? See table below — all live (Supabase-backed); none are placeholder/mock.

## Files changed (smallest safe fix)
- **`src/lib/supabaseClient.ts`** — `auth: { persistSession: true, autoRefreshToken: true,
  detectSessionInUrl: true }`. Anon client only; service-role key never in the browser; RLS
  unchanged. This makes the admin session persist + auto-refresh so authenticated queries keep a
  valid JWT → admin RLS returns the real rows.
- **`src/components/sections.tsx`** (ApprovalCenter empty state) — replaced the misleading
  *"No approvals yet…"* with an auth-aware message: if signed in but empty, advises the session may
  have expired (sign out/in, reload) and notes approvals are admin-only via RLS.

## Does this fix Approvals (and the rest)?
- **Yes.** With a persisted/refreshed admin session, `approvals` (and every other admin-RLS tab)
  returns real rows. `13eafcab` **should now appear** in Approvals as a pending Facebook item.
- **Approve/Reject already work safely** — `decideApproval` updates only `approvals.status`
  (allowed by admin RLS). It does **not** set `publish_enabled`, does **not** publish. Social
  approvals only enable a **dry-run** job. No RPC/Edge Function change needed.

## Tab status (all Supabase-backed / admin-RLS — "Live" once signed in)
| Tab | State | Reads |
|---|---|---|
| Command Center (Hermes) | Live | approvals/jobs counts + Hermes chat |
| System Health | Live | system_health |
| Agent Jobs | Live | agent_jobs, agent_registry |
| Approvals | Live (fixed) | approvals |
| GoClear / Apex | Live (may be empty if unseeded) | partner_offers, client_recommendations |
| Opportunity Lab | Live | monetization_opportunities |
| Intake & Orientation | Live | (intake tables) |
| Creative Studio | Live | creative_campaigns/briefs/assets/scores/design/publish packages |
| Design Library | Live | design_inspiration_sources, pattern_registry, feature_design_packets, ui_quality_reviews |
| Trading Lab | Live (read-only display) | trading_strategy_candidates, trading_risk_rules — no live trading from UI |
| SEO / Marketing | Live (may be empty) | seo_sites, seo_opportunities |
| Model Router | Live | model_providers, model_routes, agent_registry |
| Integrations | Live | model_providers |
| Ops & Improvements | Live | ops_incidents |
| Events Feed | Live | nexus_events |

There are **no mock/placeholder tabs** — "empty" tabs are either (a) gated by the now-fixed session
issue, or (b) live tables with no seeded rows yet.

## Safety confirmations
- Nothing published (`published: []`, `facebook_publish_enabled_false`), no email (already_sent
  dedup), no trade, no scheduler.
- `publish_enabled` remains **false**; approval `13eafcab` remains **pending** (not approved here).
- Hermes firewall untouched; service-role key not exposed; only browser-safe VITE/anon used.

## Exact next action for Ray
1. After this fix is pushed + Netlify redeploys, open `https://nexusv20.netlify.app`, **sign in**
   (sign out first if it looks stale), and open **Approvals** — `13eafcab` should appear as a
   pending Facebook item with Approve / Reject buttons.
2. The other tabs will likewise populate (where data exists).
3. To proceed with the Facebook test post, follow the one-post path (approve in UI → set
   `social_accounts.publish_enabled=true` in Supabase → `npm run nexus:watch` once → set it back to
   false). Approval alone does not publish.
