# Nexus Supabase — Browser/Live Verification

**Generated**: 2026-07-05

---

## Env Key Status

| Key | Present | Source |
|-----|---------|--------|
| `VITE_SUPABASE_URL` | YES | .env |
| `VITE_SUPABASE_ANON_KEY` | YES | .env |
| `SUPABASE_URL` | YES | .env |
| `SUPABASE_SERVICE_ROLE_KEY` | YES | .env |

---

## Client Configuration

| Check | Status |
|-------|--------|
| Client file | `src/lib/supabaseClient.ts` |
| `isSupabaseConfigured` | boolean (not function) |
| Frontend uses VITE_ keys only | YES |
| Service role key in frontend | NO |
| Auth/session detection | via `isSupabaseConfigured` |

---

## Browser-Safe Diagnostics

The Supabase client is configured with:
- `VITE_SUPABASE_URL` (40 chars)
- `VITE_SUPABASE_ANON_KEY` (208 chars)

These are safe for browser use. The `SUPABASE_SERVICE_ROLE_KEY` is NOT used in frontend code.

---

## Query Status

| Table | Status |
|-------|--------|
| client_profiles | Falls back to synthetic when unavailable |
| client_tasks | Falls back to synthetic when unavailable |
| readiness_scores | Falls back to synthetic when unavailable |
| client_documents | Returns empty when unavailable |
| research_sources | Returns empty when unavailable |
| nexus_lessons | Returns 0 when unavailable |
| nexus_events | Returns empty when unavailable |

---

## Empty State Handling

All Supabase-dependent components gracefully handle empty/unavailable data:
- Command Center cards show "No data yet" instead of mock data
- Client Portal shows synthetic demo data with clear "synthetic" label
- Data adapter returns `{ source: 'supabase' | 'synthetic' }` for transparency

---

## Classification

**ENV_PRESENT_BROWSER_EXPECTED**

- All env keys present
- Frontend uses correct keys only
- Python SSL blocks server-side verification
- Browser expected to work (different SSL stack)
- Live table status unverified

## Exact Next Step

1. Open app in browser
2. Open DevTools → Network tab
3. Navigate to any page with Supabase queries
4. Verify 200 responses
5. If successful → reclassify as VERIFIED_BROWSER_READS
