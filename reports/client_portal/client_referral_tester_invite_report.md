# Client Referral/Tester Invite Report

**Generated:** 2026-07-05  
**Status:** Specification  

## Admin Invite Flow

### Steps

1. Admin navigates to `/portal/team` or `/admin/clients`
2. Clicks "Invite Client" button
3. Fills form: email, role, access level, message
4. System generates invite token
5. Email sent with personalized link
6. Invitee clicks link → account creation or login
7. Access grant created automatically
8. Admin sees invite status (pending/accepted/expired)

### Invite Form Fields

```typescript
interface InviteForm {
  email: string;
  role: 'client' | 'team_member';
  access_level: AccessType;
  personal_message?: string;
  expires_in_days: number; // default 14
}
```

## Tester Bypass

### Tester Account Rules

- No payment required
- Full feature access
- Watermark on exported documents
- "Beta" badge in UI
- Limited to 100 tester accounts
- Auto-expire after 90 days (renewable)

### Tester Invite Process

1. Admin selects "Invite as Tester"
2. No access level selection (auto `tester`)
3. No expiration (managed separately)
4. Tester receives welcome email with beta info
5. Feedback button always visible in portal

## Referral Tracking

### Referral Model

```typescript
interface Referral {
  id: string;
  referrer_id: string;      // client who referred
  referred_email: string;
  referred_client_id: string | null; // after signup
  referral_code: string;
  status: 'pending' | 'signed_up' | 'converted';
  reward_type: 'credit' | 'feature' | 'discount';
  reward_amount: number;
  created_at: string;
  converted_at: string | null;
}
```

### Referral Flow

```
Client shares referral link → Friend clicks link →
Friend signs up → Referral tracked →
Friend converts to paid → Reward granted to both
```

### Referral Rewards

| Referrer Reward | Referred Reward |
|-----------------|-----------------|
| $10 account credit | 14-day free trial |
| 1 month free upgrade | 20% off first 3 months |
| Bonus feature unlock | Priority support |

### Referral Link Format

```
https://nexusos.app/ref/{referral_code}
```

## Invite Email Template

### Subject Lines

- "You're invited to Nexus OS - {sender_name} sent you access"
- "{sender_name} thinks you'd benefit from Nexus OS"
- "Get started with Nexus OS - invited by {sender_name}"

### Email Content

```
Hi {invitee_name},

{sender_name} from {business_name} invited you to join Nexus OS.

Nexus OS helps businesses:
• Track credit score and improve it
• Discover grants and funding opportunities
• Manage business documents securely
• Get AI-powered guidance for growth

Your invite includes:
• {access_level} access for {expires_in_days} days
• Personalized onboarding
• Direct support from our team

[Accept Invite Button]

This invite expires on {expires_at}.

Questions? Reply to this email or visit our help center.

- The Nexus OS Team
```

### Email Variants

1. **Client invite** - Focus on portal benefits
2. **Team member invite** - Focus on collaboration features
3. **Tester invite** - Focus on beta features and feedback
4. **Referral invite** - Include referrer's testimonial

## Next Actions

1. Build admin invite form component
2. Create invite API endpoint
3. Build email template system
4. Implement referral tracking database
5. Create referral link generator
6. Build referral dashboard for clients
7. Design reward fulfillment system
8. Test email deliverability
