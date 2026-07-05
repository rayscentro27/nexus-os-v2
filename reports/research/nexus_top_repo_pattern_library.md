# Top Repo Pattern Library

**Generated:** 2026-07-05  
**Status:** Curated  

## Payment Patterns

### Stripe Checkout Flow

```
User clicks "Subscribe" → Stripe Checkout session created →
Redirect to Stripe → Payment processed → Webhook received →
Subscription created → User redirected to success page
```

### Customer Portal

```
User clicks "Manage Billing" → Portal session created →
Redirect to Stripe Customer Portal → User manages subscription →
Webhook received → Local state updated
```

### Webhook Handling

```
Stripe sends event → Verify signature → Parse event →
Route to handler → Update database → Trigger side effects →
Return 200 OK
```

### Subscription Lifecycle

```
Trial → Active → Past Due → Canceled
  ↓        ↓         ↓
Renewal  Payment   Grace
         Failed    Period
```

## Document Patterns

### Upload Flow

```
User selects file → Client-side validation →
Upload to storage → Process (OCR/validate) →
Create document record → Update UI
```

### Version Control

```
New version uploaded → Previous version archived →
Version number incremented → Diff generated →
Metadata updated
```

### Permission Check

```
User requests document → Check org membership →
Check role permissions → Check document-level ACL →
Grant or deny access
```

## Credit Scoring Patterns

### Score Calculation

```
Fetch user data → Extract features →
Apply scoring model → Calculate factors →
Generate recommendations → Store score
```

### Factor Weighting

```
Payment history (35%) + Credit utilization (30%) +
Credit age (15%) + Credit mix (10%) + Inquiries (10%) = Score
```

### Trend Analysis

```
Fetch historical scores → Calculate deltas →
Identify patterns → Generate insights →
Predict future trajectory
```

## Authentication Patterns

### JWT Flow

```
User logs in → Credentials validated → JWT issued →
Token stored client-side → Token sent with requests →
Token validated server-side → Access granted
```

### Role-Based Access

```
User authenticated → Fetch roles → Check permissions →
Route to appropriate view → Enable/disable features
```

### Session Management

```
User logs in → Session created → Refresh token issued →
Access token expires → Refresh token used →
New access token issued → Session persists
```

## Notification Patterns

### Event-Driven

```
Event occurs → Check notification preferences →
Generate notification → Store in queue →
Deliver via channel (email/push/in-app) → Mark delivered
```

### Digest Mode

```
Events accumulate → Check digest schedule →
Aggregate notifications → Send digest →
Clear processed events
```

## API Design Patterns

### RESTful CRUD

```
GET /resources        → List
GET /resources/:id    → Read
POST /resources       → Create
PUT /resources/:id    → Update
DELETE /resources/:id → Delete
```

### Pagination

```
GET /resources?page=1&limit=20&sort=created_at:desc
Response: { data: [...], total: 100, page: 1, pages: 5 }
```

### Error Handling

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [...]
  }
}
```

## Dashboard Patterns

### Metric Cards

```
┌─────────┬─────────┬─────────┬─────────┐
│ Score   │ Funding │ Docs    │ Tasks   │
│ 720     │ $50K    │ 12/15   │ 3/5     │
│ ↑ 15    │ ↑ $10K  │ ↑ 2     │ ↑ 1     │
└─────────┴─────────┴─────────┴─────────┘
```

### Progress Tracking

```
[████████░░░░] 65% Complete
Step 3 of 5: Document Upload
```

### Activity Timeline

```
Today
  └─ 2:30 PM - Score updated (+15 points)
  └─ 11:00 AM - Document uploaded
Yesterday
  └─ 4:00 PM - Grant match found
  └─ 9:00 AM - Application submitted
```

## Next Actions

1. Implement Stripe checkout pattern
2. Build webhook handler with signature verification
3. Create document upload flow
4. Implement JWT authentication
5. Build notification system
6. Design dashboard layout
