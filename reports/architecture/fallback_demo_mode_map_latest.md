# Fallback/Demo Mode Map — Nexus OS v2

## Fallback Activation Chain

### Layer 1: Feature Flag
- **File**: `src/data/clientDataMode.js`
- **Flag**: `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT === 'true'`
- **Effect**: When false, `liveSupabaseTestClientEnabled = false`, `supabaseLiveReadsEnabled = false`, `internalLabel = 'Demo/fallback data'`
- **Can hide live data**: YES — entire live data cascade is disabled

### Layer 2: Auth Gate
- **File**: `src/clientPortal/useClientPortalData.ts`
- **Gate**: `if (!isSupabaseConfigured || !clientDataMode.liveSupabaseTestClientEnabled || !userId) return`
- **Can hide live data**: YES — skips `useSupabaseClientData` effect entirely

### Layer 3: Service Short-Circuit
- **File**: `src/services/clientDashboardLiveData.ts`
- **Gate**: `if (!clientDataMode.liveSupabaseTestClientEnabled) return { enabled: false, ...empty }`
- **Can hide live data**: YES — returns empty arrays before any query

### Layer 4: Adapter-Level Fallback
- **File**: `src/lib/clientPortalDataAdapter.ts`
- **Gate**: `if (isSupabaseConfigured && supabase) { try { ... } catch { ... } } return synthetic`
- **Can hide live data**: YES — returns synthetic data when query errors or returns no rows
- **Hardcoded ID**: `DEMO_CLIENT_ID = 'client_test_julius_erving'`

### Layer 5: Static Data
- **File**: `src/data/clientPortalData.js`
- **Gate**: Always loaded as base data
- **Hardcoded ID**: `DEMO_CLIENT_ID = 'client_demo_001'`, `DEMO_TENANT_ID = 'tenant_demo_goclear'`
- **Can hide live data**: YES — merged over live data when `canLoadLive` is false

### Layer 6: UI Label Fallback
- **File**: `src/components/client/ClientPortalShell.jsx`
- **Label**: `liveStatusLabel` computed from `liveStatus` context
- **Values**: `'connected' → 'Live data connected'`, `'loading' → 'Live data pending'`, else `'Demo/fallback data'`

## All Fallback/Demo Instances

| File | Line | Pattern | What Fallback Does | When Activated | Can Hide Live Data | Should Remain | Recommended Fix |
|------|------|---------|-------------------|----------------|-------------------|---------------|-----------------|
| `src/data/clientDataMode.js` | 8 | `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT` | Gates all live reads | Env var not `'true'` | YES | YES (feature flag) | None |
| `src/data/clientDataMode.js` | 10-20 | `clientDataMode` object | Provides mode flags to all components | Always | NO (just flags) | YES | None |
| `src/data/clientPortalData.js` | 3-4 | `DEMO_CLIENT_ID`, `DEMO_TENANT_ID` | Hardcoded demo IDs | Adapter fallback | YES | Partially | Replace with resolved client ID when live |
| `src/data/clientPortalData.js` | 27-61 | `clientPortalData` object | Complete demo dataset | When live disabled | YES | YES (fallback) | None |
| `src/lib/clientPortalDataAdapter.ts` | 16 | `DEMO_CLIENT_ID = 'client_test_julius_erving'` | Fallback client ID for queries | Adapter fallback | YES | Partially | Use resolved context instead |
| `src/lib/clientPortalDataAdapter.ts` | 22-97 | `loadClientProfile()` | Returns synthetic profile on error/empty | Query fails or no rows | YES | YES (fallback) | None |
| `src/lib/clientPortalDataAdapter.ts` | 99-117 | `loadClientTasks()` | Returns synthetic tasks on error/empty | Query fails or no rows | YES | YES (fallback) | None |
| `src/lib/clientPortalDataAdapter.ts` | 119-137 | `loadReadinessScores()` | Returns synthetic scores on error/empty | Query fails or no rows | YES | YES (fallback) | None |
| `src/lib/clientPortalDataAdapter.ts` | 139-157 | `loadClientDocuments()` | Returns empty synthetic on error/empty | Query fails or no rows | YES | YES (fallback) | None |
| `src/services/clientDashboardLiveData.ts` | 13-14 | `TEST_CLIENT_ID`, `TEST_TENANT_ID` | Hardcoded fallback IDs | Context resolution fails | YES | Partially | Keep as last resort; prefer resolved context |
| `src/services/clientDashboardLiveData.ts` | 16-18 | `feature_disabled` return | Short-circuits all queries | Env flag off | YES | YES (expected) | None |
| `src/clientPortal/useClientPortalData.ts` | 33 | Supabase gate | Skips live data effect | Env off or no userId | YES | YES (expected) | None |
| `src/clientPortal/useClientPortalData.ts` | 119 | Preview skip | Skips auth effect | `isPreview = true` | YES | YES (preview mode) | None |
| `src/pages/client/ClientPortalPages.jsx` | Multiple | `data.*` references | Uses static `clientPortalData` | Live data unavailable | YES (by design) | YES | None |
| `src/components/client/ClientPortalShell.jsx` | 273 | `liveStatusLabel` | Computes badge text | Based on `liveStatus` | NO (just label) | YES | None |
| `src/components/ClientsPanel.jsx` | Multiple | `clientsData` fallback | Static client list for admin drawer | Live data unavailable | NO (admin-only) | YES | None |
| `src/admin/NexusAdminUI.jsx` | 4-5 | `runtime`, `nexusEngineStatusData` imports | Bundled JSON snapshots | Always loaded | NO (admin-only) | YES | None |

## Hardcoded Client IDs Summary

| ID | File | Purpose | Risk |
|----|------|---------|------|
| `client_test_julius_erving` | `clientPortalDataAdapter.ts`, `clientDashboardLiveData.ts` | Fallback test client | Medium — may show wrong data if context fails |
| `client_demo_001` | `clientPortalData.js` | Static demo client ID | Low — only used in fallback mode |
| `tenant_demo_goclear` | `clientPortalData.js`, `clientDashboardLiveData.ts` | Static demo tenant ID | Low — only used in fallback mode |
| `client_demo_julius` | `clientsData.js` | Admin client list demo | Low — admin-only fallback |

## Recommendations

1. **Priority 1**: Remove `client_test_julius_erving` from `clientDashboardLiveData.ts` as primary path. Make it a true last-resort fallback after context resolution fails.
2. **Priority 2**: Ensure `clientPortalDataAdapter.ts` uses resolved client context instead of hardcoded IDs.
3. **Priority 3**: Audit `clientsData.js` for hardcoded demo client IDs in admin context.
4. **Priority 4**: Add warning log when fallback mode is activated, so debugging is easier.
