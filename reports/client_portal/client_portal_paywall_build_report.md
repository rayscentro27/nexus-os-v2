# Client Portal Paywall Build Report

**Generated:** 2026-07-05  
**Status:** Planning  

## Access Types Defined

| Type | Description | Access Level |
|------|-------------|--------------|
| `free` | Basic portal access | Dashboard, limited score view |
| `starter` | Core features | Score, docs, basic funding |
| `growth` | Full features | All sections, team, grants |
| `agency` | Multi-client | Client management, billing |
| `tester` | Beta access | Full features, no billing |
| `invited` | Pre-payment | Limited trial, upgrade prompt |

## Stripe Test-Mode Readiness

- Test key configured in `.env`: `STRIPE_TEST_KEY`
- Products defined in Stripe dashboard (test mode)
- Price IDs mapped to access levels
- Webhook endpoint ready: `/api/webhooks/stripe`
- Subscription create/cancel/upgrade flows

### Test Cards

```
Success: 4242 4242 4242 4242
Decline: 4000 0000 0000 0002
3D Auth: 4000 0025 0000 3155
```

## Invite Bypass System

### Admin Invite Flow

1. Admin creates invite in dashboard
2. System generates unique invite token
3. Invitee receives email with portal link + token
4. Token grants temporary `invited` access level
5. Upgrade prompt appears on paywall-protected sections
6. Token expires after 14 days

### Bypass Rules

- Admin users can bypass all paywalls
- Tester accounts have full access
- Invited users see upgrade prompts, not blocks
- Demo mode shows all features with watermarks

### Invite Data Model

```typescript
interface ClientInvite {
  id: string;
  email: string;
  org_id: string;
  role: 'client' | 'team_member';
  access_level: AccessType;
  token: string;
  expires_at: string;
  accepted_at: string | null;
  created_by: string;
}
```

## Subscription Value Research Summary

See dedicated subscription value research report.

Key finding: Clients pay monthly for **ongoing value**, not one-time access.

## Next Actions

1. Build paywall guard component
2. Implement Stripe checkout flow
3. Create invite management UI
4. Add upgrade prompt modals
5. Build access level middleware
6. Test with Stripe test cards
7. Create billing portal page
