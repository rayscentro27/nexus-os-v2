# Real Tester Data Readiness

**Generated:** 2026-07-07

## Assessment

**Status: Ready for manual creation (Option A)**

### Option A: Manual Creation — READY

Ray can create tester accounts now using:
1. Supabase Dashboard → Authentication → Users
2. Bootstrap trigger auto-creates profiles and memberships
3. Manual profile updates for tester-specific data

### Option B: Script-Based — READY (Dry-Run)

- Script created: `scripts/testers/seed_test_client_template.py`
- Dry-run by default
- Requires `--write` flag and env vars to execute
- No real data committed

### Option C: Live Automated — NOT READY

Requires:
- All env vars confirmed
- Script tested with single user first
- Password reset workflow verified

## What's Ready

- ✅ Auth bootstrap trigger (auto-creates profiles)
- ✅ Tenant memberships
- ✅ Client profiles
- ✅ RLS policies
- ✅ Document upload
- ✅ Hermes guidance
- ✅ Email notifications (Resend)
- ✅ Admin review UI

## What's Not Ready

- ❌ Stripe product/price IDs (needed for paid testers)
- ❌ Social tokens (not needed for basic testers)
- ❌ Real client data (by design — testers use placeholder data)

## Recommendation

Create 3-5 testers manually via Supabase Dashboard first. Verify login, upload, and guidance work. Then expand to 10.
