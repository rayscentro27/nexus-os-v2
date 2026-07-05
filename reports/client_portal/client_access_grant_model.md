# Client Access Grant Model

**Generated:** 2026-07-05  
**Status:** Specification  

## Access Types

```typescript
type AccessType = 'free' | 'starter' | 'growth' | 'agency' | 'tester' | 'invited';
```

| Type | Price | Features |
|------|-------|----------|
| `free` | $0 | Dashboard, limited score |
| `starter` | $29/mo | Full score, docs, funding list |
| `growth` | $79/mo | Everything + grants, team |
| `agency` | $149/mo | Multi-client, billing mgmt |
| `tester` | $0 (beta) | Full access, no billing |
| `invited` | $0 (trial) | Time-limited full access |

## Grant Model

```typescript
interface AccessGrant {
  id: string;
  client_id: string;
  org_id: string;
  access_type: AccessType;
  granted_by: 'subscription' | 'invite' | 'admin' | 'promo';
  granted_at: string;
  expires_at: string | null;
  stripe_subscription_id: string | null;
  invite_id: string | null;
  is_active: boolean;
}
```

### Grant Rules

1. One active grant per client per org
2. Subscription grants auto-renew
3. Invite grants expire after 14 days
4. Admin grants have no expiration
5. Promo grants can have custom expiration

## Invite Model

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
  created_at: string;
}
```

### Invite Flow

```
Admin creates invite → Token generated → Email sent →
Invitee clicks link → Token validated → Account created/linked →
Access grant created → Portal access enabled
```

## Subscription Status Model

```typescript
interface SubscriptionStatus {
  client_id: string;
  stripe_customer_id: string;
  subscription_id: string | null;
  status: 'active' | 'past_due' | 'canceled' | 'trialing' | 'none';
  current_period_start: string;
  current_period_end: string;
  cancel_at: string | null;
  plan_id: string;
  access_level: AccessType;
}
```

### Status Transitions

```
none → active (first payment)
active → past_due (payment failed)
past_due → active (payment recovered)
past_due → canceled (grace period ended)
active → canceled (user cancels)
none → trialing (free trial started)
trialing → active (trial converted)
trialing → canceled (trial expired)
```

## Next Actions

1. Create Supabase migration for `access_grants` table
2. Create Supabase migration for `client_invites` table
3. Create Supabase migration for `subscriptions` table
4. Build access check middleware
5. Build invite management API
6. Build subscription webhook handler
