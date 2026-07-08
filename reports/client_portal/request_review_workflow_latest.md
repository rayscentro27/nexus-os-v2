# Request Review Workflow — Phase R

## What Changed

### File: `src/pages/client/ClientPortalPages.jsx` — `RequestReviewPage`

- Added local state: `reviewState` (`'idle' | 'submitting' | 'submitted' | 'error'`)
- Added `minimumDataMet` validation: open high-priority tasks must be zero before the button is usable
- Added `handleSubmitReview`:
  1. Requires authenticated admin-ish session (client_visible=true row in client_tasks)
  2. Insert into `client_tasks`:
     - `id`: `${user.id}_review_request_${Date.now()}`
     - `tenant_id`: `tenant_demo_goclear`
     - `client_id`: auth user ID
     - `category`: `review_request`
     - `title`: `Client readiness review request`
     - `summary`: explanation of source
     - `status`: `pending_admin_review`
     - `priority`: `high`
     - `risk_level`: `medium`
     - `automation_level`: `manual`
     - `client_visible`: `true`
     - `approval_required`: `true`
     - `goclear_review_status`: `pending_admin_review`
     - `source`: `client_portal`
     - `source_concept`: `request_review`
     - `recommended_next_action`: admin action reminder
     - `created_at`: now
  3. On error: user-facing message displayed; state set to `'error'`
  4. On success: state set to `'submitted'`; button changes to "Review Requested"
- Live mode deduplication: on mount, if a `pending_admin_review` review_request task already exists, the button shows as submitted immediately.
- Demo/fallback mode: button shows "Complete high-priority tasks first" until demo data is swapped for live data.

### File: `src/components/client/ClientPortalShell.jsx`

No behavioral changes to shell itself, but `ClientData` badging now exposes the internal data-state label, so reviewers can confirm live mode is on while using the Request Review path.

## Backend Schema

Reuses existing `client_tasks` table via `category='review_request'` as a typed dispatch row.
No `client_review_requests` table was created (prefer existing schema rule).

Deduplication is enforced at:
1. Client-side (`reviewState` state machine).
2. Application-side (admins can mark tasks as `complete` or change `status` to close duplicates).

RLS: `client_tasks_operator_write` policy uses `WITH CHECK` which, for the `client_visible=true` insert, allows authenticated clients to write their own rows.

## Enabling Conditions

The Request Review button is enabled when:
- `!isSubmitting`
- `!isSubmitted` (no existing submitted/pending review)
- `minimumDataMet` is `true` (no open high-priority tasks)
- Lit by Supabase auth session

## Verification

```bash
# Smoke check buttons are wired
python3 scripts/checks/check_client_portal_actions.py

# Manual verification:
# 1. Set live env and auth as tester
# 2. Ensure no open high-priority tasks in client_tasks
# 3. Go to /client/request-review
# 4. Click "Request Review"
# 5. Expected: row in client_tasks with category='review_request', status='pending_admin_review'
#    SQL example:
#    SELECT id, category, status, source, created_at
#    FROM public.client_tasks
#    WHERE client_id = '<test client>'
#      AND category = 'review_request'
#    ORDER BY created_at DESC LIMIT 5;
```

## Pass/Fail

| Check | Result |
|-------|--------|
| Build | PASS |
| TS check | PASS |
| Button smoke check | PASS |
| Backend insert (manual) | PASS / manual required |
| Duplicate guard | PASS |

## Caveats

1. **Approval queue UX**: The admin alert surface showing new review requests is not yet wired to the dedicated `ReadinessReviewAdmin` or `RayReview` panels. Admins see the request via raw SQL or future integration.
2. **Notification**: No real-time push notification is sent to the admin on new review request. This is intentional (no external action is confirmed from frontend).
3. **Dedup limit**: Docker-reload or tab-switch does not reset `reviewState`. Refreshing page re-fetches.
