# Client Portal Live Data Adapter Report

**Generated:** 2026-07-05  
**Status:** Created  

## Adapter Created

`src/adapters/clientPortalDataAdapter.ts`

## Architecture

```
ClientPortalDataAdapter
├── getClients()           → Supabase query or synthetic
├── getClientById(id)      → Single client lookup
├── getClientScore(id)     → Credit score + factors
├── getClientDocuments(id) → Document vault listing
├── getClientFunding(id)   → Funding applications
├── getClientGrants(id)    → Grant matches
└── getClientActivity(id)  → Activity timeline
```

## Supabase Queries

```typescript
// Client list
supabase.from('clients').select('*').eq('org_id', orgId)

// Credit score
supabase.from('credit_scores').select('*').eq('client_id', id).order('created_at', { ascending: false }).limit(1)

// Documents
supabase.from('documents').select('*').eq('client_id', id).order('uploaded_at', { ascending: false })

// Funding applications
supabase.from('funding_applications').select('*').eq('client_id', id)

// Grant matches
supabase.from('grant_matches').select('*').eq('client_id', id).eq('status', 'active')
```

## Synthetic Fallback

When Supabase is unavailable or tables don't exist:

```typescript
const syntheticClient = {
  id: 'demo-001',
  name: 'Demo Client',
  email: 'demo@nexus.test',
  business_name: 'Demo Business LLC',
  score: { value: 72, factors: [...] },
  documents: [...],
  funding: [...],
  grants: [...]
}
```

## Data Sources Mapped

| Data Point | Supabase Table | Fallback |
|------------|----------------|----------|
| Client profile | `clients` | Synthetic client |
| Credit score | `credit_scores` | Mock score (680) |
| Documents | `documents` | Empty array |
| Funding apps | `funding_applications` | Demo applications |
| Grants | `grant_matches` | Sample grants |
| Activity | `activity_log` | Generated timeline |
| Team members | `team_members` | Owner only |
| Subscription | `subscriptions` | Free tier |

## Next Actions

1. Verify Supabase tables exist or create migrations
2. Add real-time subscriptions for live updates
3. Implement caching layer (React Query / SWR)
4. Add error boundary for failed queries
5. Build offline-first fallback queue
