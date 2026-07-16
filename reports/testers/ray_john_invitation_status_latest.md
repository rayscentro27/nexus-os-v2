# Ray John — Trusted Tester Invitation Status

**Generated:** 2026-07-16T14:00:00Z  
**Commit:** `10e87955394c4f5afd3a5f5e9b98c24823ae18d4`  
**Branch:** `main`  
**Phase:** 7.2 — Friends & Family Preview Program

---

## Current Invitation (Active)

| Field | Value |
|-------|-------|
| Invitation ID | `8e75040d-4ac2-4325-9ff8-5924e84fcc68` |
| Tester Name | Ray John |
| Tester Email | `ray@onechoiceaz.com` |
| Testing Level | `friends_family_free` |
| Invitation Status | `approved` |
| Payment Mode | `none` (Free Preview) |
| Max Sessions | 3 |
| Sessions Used | 0 |
| Expires | 14 days from creation |
| Personal Note | Included |

## Previous Invitation (Revoked)

| Field | Value |
|-------|-------|
| Invitation ID | `8127d08a-7aaf-4400-bfe5-c8c8992aaa09` |
| Testing Level | `invited_test_mode` |
| Status | `revoked` |
| Reason | Replaced with Friends & Family Free Preview invitation |

## Email Delivery Status

| Attempt | Status | Notes |
|---------|--------|-------|
| Previous (old invitation) | Sent (2 attempts) | Template was Stripe-focused, used Netlify URLs |
| New (corrected) | **Awaiting send** | Personal email from Ray Davis, GoClear branding, canonical domain |

## Invitation Flow

1. **Admin creates invitation** → `friends_family_free` type, 3 sessions, 14 days, personal note
2. **Email sent** → Personal email from Ray Davis via `send-tester-invitation` edge function
3. **Ray clicks link** → `https://goclearonline.cc/invite/<token_hash>`
4. **Welcome page** → Shows GoClear introduction, invitation details, "Create My Account" button
5. **Password setup** → `/invite/accept?token=<hash>` — creates Supabase auth user
6. **Full journey** → Credit profile, document vault, business setup, Clyde guidance, referrals

## What Changed (Phase 7.2)

- ✅ Invitation type: `friends_family_free` (was `invited_test_mode`)
- ✅ Email template: Personal from Ray Davis (was Stripe-focused system notification)
- ✅ Domain: `goclearonline.cc` (was `nexusv20.netlify.app`)
- ✅ Flow: One-click via URL path (was manual token entry)
- ✅ Sessions: 3 (was 1)
- ✅ Expiry: 14 days (was 7 days)
- ✅ Personal message: Included

## Pilot Controls State

| Control | Value |
|---------|-------|
| invitations_enabled | true |
| test_mode_purchases_enabled | true |
| controlled_live_pilot_enabled | false |
| public_live_enabled | false |
| hidden_pilot_offer_enabled | false |
| emergency_checkout_disabled | false |

## Safety Checks

| Check | Result |
|-------|--------|
| No live payment orders exist | PASS |
| Public live disabled | PASS |
| Controlled live pilot disabled | PASS |
| Real payments not processed | PASS |
| Canonical domain enforced | PASS |
| All safety checks | **PASSED** |

## Next Steps

- [ ] Send corrected invitation to `ray@onechoiceaz.com` (Phase 21)
- [ ] Ray receives email, clicks link, creates account
- [ ] Ray completes full GoClear journey in Free Preview mode
- [ ] Ray provides feedback on invitation experience
