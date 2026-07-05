# Nexus Client Portal — Prompt 2 Closeout

**Generated**: 2026-07-05

---

## Pages/Components That Exist

| File | Purpose | Data Source |
|------|---------|------------|
| `src/components/client/ClientPortalShell.jsx` | Main portal shell/layout | Local |
| `src/components/client/ClientGuidePanel.jsx` | Client guide/instructions | Local |
| `src/components/client/ClientPortalUI.jsx` | UI rendering | Local |

---

## Data Adapter (Prompt 2 Created)

`src/lib/clientPortalDataAdapter.ts` provides 4 async functions:

| Function | Supabase Table | Synthetic Fallback |
|----------|---------------|-------------------|
| `loadClientProfile()` | `client_profiles` | Julius Erving (Demo) profile |
| `loadClientTasks()` | `client_tasks` | 4 demo tasks |
| `loadReadinessScores()` | `readiness_scores` | 4 demo scores |
| `loadClientDocuments()` | `client_documents` | Empty array |

**All functions return `source: 'supabase'` or `source: 'synthetic'` so consumers know which data they're getting.**

---

## What Prompt 2 Actually Built

- ✅ Data adapter with Supabase queries + synthetic fallback
- ✅ Type definitions for ClientProfile, ClientTask, ReadinessScore, ClientDocument
- ✅ Demo client ID `client_test_julius_erving` for synthetic mode
- ✅ `getClientDataSource()` helper

---

## What Prompt 2 Did NOT Build

- ❌ Premium shell design (screenshot-level quality)
- ❌ No-scroll desktop layout
- ❌ Real client data flow (depends on Supabase being live)
- ❌ Stripe checkout integration
- ❌ Client invite/bypass flow
- ❌ Onboarding wizard
- ❌ Credit report upload UI
- ❌ Business setup wizard
- ❌ Funding readiness assessment UI

---

## Paywall / Access Model

The paywall/access grant model was designed in earlier reports:
- 8 access types defined
- Stripe test-mode not yet connected (keys in `.env.nexus.recovered.local` only)
- Invite bypass designed but not implemented
- Subscription value researched ($97/mo core tier estimate)

---

## What Remains

1. **Supabase must be live** before client portal shows real data
2. Premium shell design (Got Funding quality level)
3. No-scroll desktop layout
4. Stripe test-mode checkout
5. Client invite/bypass flow
6. Onboarding wizard
7. All client-facing UIs (credit, business, funding)
