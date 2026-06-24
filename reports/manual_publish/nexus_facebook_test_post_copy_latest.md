# Nexus — Facebook Test Post Copy (live URL added)

- generated_at: 2026-06-24
- approval: 13eafcab-6940-4612-8239-54786e8c9e60 (facebook_publish_enablement) — **status: pending**
- account: Clear Credentials (facebook) — **publish_enabled: false**
- build: PASS · nexus:watch: PASS · published: [] (nothing published)

> Live "latest" copy: gitignored `reports/runtime/nexus_facebook_test_post_copy_latest.md`.
> Committed copy (this file): tracked `reports/manual_publish/`.

---

## Where the post copy lives / was updated
The Facebook post copy is **generated in code**, not stored as a pending Supabase row (no
`social_post` exists yet because `publish_enabled=false`). The real publish path pulls
`facebook_post.copy` from `creative_drafts()` in **`scripts/run_nexus_continuous_operations.py`**.

- **Updated:** the `facebook_post` draft `copy` in `scripts/run_nexus_continuous_operations.py`
  (only that one draft — Instagram/TikTok/email/landing drafts unchanged).
- **Regenerated (derived):** `reports/manual_publish/goclear_apex_social_manual_publish_package.json`
  / `.md` now contain the new copy (verified the live URL is present).

## What changed
Replaced the old DM/email-only CTA with the approved copy that links to the live landing page
`https://nexusv20.netlify.app/goclear-apex-readiness.html`, keeping it readiness-framed and
non-guaranteeing. The compliance `DISCLAIMER` line is still appended.

## Final safe post copy
```
Small business owners: before you apply for funding, make sure your credit and business profile are actually ready.

GoClear/Apex now has a $97 Credit & Funding Readiness Review to help identify gaps before you waste time applying.

Start here:
https://nexusv20.netlify.app/goclear-apex-readiness.html

No funding guarantees. This is a readiness review to help you understand what needs to be fixed or prepared first.

Education/readiness only. No guaranteed funding, approval, score change, or deletion outcome.
```

## Safety confirmations (verified live)
- **Nothing published** — watch reported `published: []`, `blocked: ["facebook_publish_enabled_false"]`.
- **publish_enabled remains false** — Clear Credentials row, confirmed via Supabase.
- **Approval remains pending** — `13eafcab` status `pending`, not approved by this task.
- No email sent (newsletter `already_sent` dedup), no trade placed, no scheduler started.
- Gates unchanged: Clear Credentials Page allowlist, linked-approval gate, token required (never
  printed), `publish_enabled` master gate still off.

## Exact next step for Ray (when ready — still one-post gated)
1. Approve `13eafcab` in the deployed app: `https://nexusv20.netlify.app` → **Approvals** → Approve
   *"Enable one Facebook GoClear/Apex test post"*.
2. Enable for exactly one post: Supabase → Table Editor → `social_accounts` → Clear Credentials →
   set `publish_enabled = true`.
3. Run `npm run nexus:watch` **once**, confirm the post + link.
4. Set `publish_enabled = false` again (no dedup — leaving it on would repost on the next run). No
   scheduler, no paid boost, one post only.
