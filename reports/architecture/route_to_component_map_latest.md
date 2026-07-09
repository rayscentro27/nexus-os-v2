# Route-to-Component Map — Nexus OS v2

## Route Registry

### Public Routes

| Route | Component | Auth | Role | Fallback | Status |
|-------|-----------|------|------|----------|--------|
| `/` | `GoClearLandingPage` | None | None | Static landing | LIVE |
| `/goclear` | `GoClearLandingPage` | None | None | Static landing | LIVE |
| `/goclear/signup` | `GoClearSignupPage` | None | None | Static form | LIVE |
| `/goclear/pricing` | `GoClearPricingPage` | None | None | Static pricing | LIVE |
| `/goclear/login` | `GoClearLoginPage` | None | None | Static login | LIVE |
| `/client/login` | `ClientLoginPage` | None | None | Supabase auth form | LIVE |
| `/client/preview` | `ClientPreviewPage` | None | None | Static preview | BROKEN (file missing) |
| `/update-password` | `UpdatePasswordPage` | Recovery session | Any | Password reset form | LIVE |

### Private Client Routes

| Route | Component | Auth | Role | Fallback | Status |
|-------|-----------|------|------|----------|--------|
| `/client` | `ClientPortalRoot` → `ClientPortalShell` + `ClientDashboard` | Required | `client` via `tenant_memberships` | Demo data from `clientPortalData.js` | PARTIAL |
| `/client/dashboard` | `ClientDashboard` | Required | `client` | Demo readiness scores | PARTIAL |
| `/client/credit-profile` | `CreditProfilePage` | Required | `client` | Demo credit data | FALLBACK |
| `/client/credit-utilization` | `CreditUtilizationPage` | Required | `client` | Demo utilization data | FALLBACK |
| `/client/documents` | `ClientDocumentsPage` | Required | `client` | Demo document lists | PARTIAL |
| `/client/business-setup` | `BusinessSetupPage` | Required | `client` | Demo business data | FALLBACK |
| `/client/business-bankability` | `BusinessBankabilityPage` | Required | `client` | Demo banking data | FALLBACK |
| `/client/funding-readiness` | `FundingReadinessPage` | Required | `client` | Demo funding data | FALLBACK |
| `/client/recommendations` | `RecommendationsPage` | Required | `client` | Demo opportunities | FALLBACK |
| `/client/resources` | `ResourcesPage` | Required | `client` | Demo resources/tools | FALLBACK |
| `/client/request-review` | `RequestReviewPage` | Required | `client` | Demo task list | PARTIAL |
| `/client/messages` | `ClientMessagesPage` | Required | `client` | Demo messages (read-only) | FALLBACK |
| `/client/settings` | `ClientSettingsPage` | Required | `client` | Demo profile | FALLBACK |

### Private Admin Routes

| Route | Component | Auth | Role | Fallback | Status |
|-------|-----------|------|------|----------|--------|
| `/admin` | `AdminGuard` → `AuthGate` → `NexusAdminUI` | Required | `admin`/`operator`/`super_admin` via `admin_users` or `tenant_memberships` | None (access denied) | LIVE (guarded) |
| `/admin/command-center` | Same as above (hash route `#command`) | Required | Same | None | LIVE (guarded) |

## Route Implementation Notes

- **Custom router**: No external router library. `App.tsx` uses `window.location.pathname` matching.
- **Portal inner router**: `ClientPortalRoot.jsx` uses `window.history.pushState` + `popstate` for SPA navigation.
- **Admin inner router**: `NexusAdminUI.jsx` uses hash-based routing (`window.location.hash`).
- **Unknown routes**: Redirect to `/`.

## Auth Gate Details

| Gate | File | Behavior |
|------|------|----------|
| `ClientPortalGate` | `src/app/App.tsx` | Redirects unauthenticated to `/client/login` |
| `AuthGate` | `src/components/auth.tsx` | Shows sign-in form if no session; supports password recovery |
| `AdminGuard` | `src/components/auth/AdminGuard.tsx` | Checks `admin_users` then `tenant_memberships` roles; shows "Checking admin access…" while loading |
| `useSession` | `src/components/auth.tsx` | Wraps Supabase auth state; handles `PASSWORD_RECOVERY` event |

## Known Route Gaps

1. `/client/preview` references `ClientPreviewPage` but file does not exist on disk — returns 404/blank.
2. `/client/messages` exists in `clientPageMap` but uses demo read-only data; no outbound messaging.
3. `/client/settings` exists in `clientPageMap` but only renders demo profile data.
4. Header icon buttons (Notifications, Messages, Help) all navigate to `/client/resources` — misrouted.
