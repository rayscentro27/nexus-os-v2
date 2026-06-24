# Nexus — Facebook One-Post Approval Path

- generated_at: 2026-06-24
- build: PASS · nexus:watch: PASS (Facebook still gated — `published: []`, `facebook_publish_enabled_false`)
- live landing page (target link): https://nexusv20.netlify.app/goclear-apex-readiness.html

> Live "latest" copy: gitignored `reports/runtime/nexus_facebook_approval_path_latest.md`.
> Committed copy (this file): tracked `reports/manual_publish/`.

---

## 1. Does the approval exist? — YES (verified live in Supabase)
```
approvals row:
  id:        13eafcab-6940-4612-8239-54786e8c9e60
  item_type: facebook_publish_enablement
  status:    pending          ← not yet approved
  title:     Enable one Facebook GoClear/Apex test post
  lane:      social
  decided_at: null
```

## 2. Where approvals are stored
- **Supabase `approvals` table** is the source of truth. RLS admin-only.
- The deployed app reads/writes it; the watch runner reads it for status.

## 3. Exact approval location / UI route
- **Deployed app → "Approvals" tab** (sidebar, ✓ icon, "Approve / reject / request changes").
  Route is rendered by `ApprovalCenter` (`src/components/Shell.tsx` key `approvals`).
- Open `https://nexusv20.netlify.app` → sign in as admin → **Approvals** → find
  *"Enable one Facebook GoClear/Apex test post"* → click **Approve**.
- The Approve button calls `decideApproval(id, 'approved')` → sets `approvals.status = 'approved'`
  and writes an `approval_approved` event. (Reject / Request-changes also available.)

## 4. Can Hermes chat approve it? — NO
- Hermes chat's "approved / yes please / do it" only files a **pending task_request** that Hermes
  itself proposed in that conversation (`isApproval` → `fileTask(pendingAction)`). It does **not**
  touch the `approvals` table, so it **cannot** approve `13eafcab`.
- Approve it on the **Approvals page** (or a direct Supabase status update). Not via chat.

## 5. Is backend execution wired? — YES, but decoupled from this approval row
- Real publishing is wired: `nexus:watch` → `activation_test_post()` →
  `scripts/social/facebook_publisher.publish(post_id, real_publish=True)` → Graph API post.
- **Important:** approving `13eafcab` is the *human go-ahead record*. It does NOT by itself set
  `publish_enabled`. The **code gate that actually allows a real post** is
  `social_accounts.publish_enabled = true`. These are decoupled — approving the row in the UI does
  not flip `publish_enabled`.

### The real publish gate chain (all must pass, in `facebook_publisher.publish`)
1. `real_publish=True` (the runner passes this).
2. platform == facebook, caption present.
3. The **linked social_post's** approval is `approved` (runner auto-creates that as approved).
4. Account is **Clear Credentials** — `account_id == ALLOWED_FB_PAGE_ID (131069194210954)` allowlist.
5. `social_accounts.publish_enabled == true`  ← **currently false**.
6. Page token present (`META_PAGE_ACCESS_TOKEN`) — token never printed.

## 6. Current state (safe identifiers only — no tokens/secrets)
| Field | Value |
|---|---|
| FB account_name | **Clear Credentials** |
| platform | facebook |
| account_id (public Page id) | 131069194210954 |
| **publish_enabled** | **false** ← still gated |
| token_env_key | META_PAGE_ACCESS_TOKEN (name only; token not shown) |
| Approval `13eafcab` | pending |

## 7. ⚠️ Two gaps to fix BEFORE enabling
1. **No UI button sets `publish_enabled`.** The Approvals page only updates the approval *status*
   (and can queue a *dry-run* job). Flipping `publish_enabled=true` for the Clear Credentials row is
   a **separate Supabase update** (Table Editor or a one-off script).
2. **The generated FB post copy does NOT contain the live URL.** The draft uses DM/reply CTAs, not a
   link to `https://nexusv20.netlify.app/goclear-apex-readiness.html`. As written, a published test
   post would not link to the landing page. The link must be added to the post copy before the real
   post (small copy edit — not done here).
3. **No one-post dedup.** Once `publish_enabled=true`, **every** `nexus:watch` run inserts a new
   social_post and publishes again (unlike the newsletter, which dedups). "One post" is only
   guaranteed by enabling → running watch **once** → disabling again. Do not leave it enabled, and
   do not run a scheduler.

## 8. Safest next step for Ray (recommended order)
1. **Approve the request** in the deployed app: Approvals → *Enable one Facebook GoClear/Apex test
   post* → **Approve**. (Records the human go-ahead; still safe — nothing publishes.)
2. **Add the live URL to the post copy** so the test post links to
   `https://nexusv20.netlify.app/goclear-apex-readiness.html` (copy edit — ask me to do it).
3. **Enable for exactly one post**: set `social_accounts.publish_enabled = true` for the Clear
   Credentials row (Supabase Table Editor), run `npm run nexus:watch` **once**, confirm the post,
   then **set `publish_enabled = false` again**.
4. Keep paid boost off, no scheduler, one post only.

### Exact actions
- **UI approve:** `https://nexusv20.netlify.app` → Approvals → Approve `13eafcab`.
- **Enable (one post):** Supabase → Table Editor → `social_accounts` → Clear Credentials row →
  `publish_enabled = true` → `npm run nexus:watch` (once) → set `publish_enabled = false`.
- (Optional dry-run first: Approvals page can queue a `social_publish` **dry_run** job; run
  `scripts/run_social_publish_job.py --dry-run` to preview blockers without posting.)

## 9. Gates that remain active (safety)
- `publish_enabled=false` (master publish gate) — still off.
- Clear Credentials Page allowlist (`ALLOWED_FB_PAGE_ID`) — cannot post to any other page.
- Linked-approval-must-be-approved gate inside the publisher.
- Token required and never printed.
- No scheduler installed/started; watch is manual and bounded.
- Approval `13eafcab` is pending — nothing publishes until Ray acts.
