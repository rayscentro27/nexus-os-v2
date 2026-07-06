# GoClear Supabase Auth Browser Audit

**Date**: 2026-07-06
**Starting commit**: `5e8140e`
**Branch**: `main`

---

## Preflight Results

| Check | Status |
|-------|--------|
| `pwd` | `/Users/raymonddavis/nexus-os-v2` |
| `git branch` | `main` |
| `npm run build` | PASS (1769 modules, 14.78s) |
| Git status | 17 modified files, 30+ untracked (alpha/reports/runtime) |

## Architecture Summary

### Supabase Client (`src/lib/supabaseClient.ts`)
- Uses ONLY `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
- `persistSession: true`, `autoRefreshToken: true`, `detectSessionInUrl: true`
- Service role key is NEVER imported in frontend
- Exports `isSupabaseConfigured` boolean for UI gating

### Auth Components (`src/components/auth.tsx`)
- `useSession()` hook: checks `getSession()` + `onAuthStateChange`
- `AuthGate`: protects admin dashboard only (root route)
- `SignInForm`: admin sign-in with password reset
- `UpdatePasswordForm`: recovery session password change
- `UserMenu`: sign out button

### GoClear Auth (`src/pages/goclear/GoClearPublicPages.tsx`)
- **Signup**: `supabase.auth.signUp()` with `full_name` + `business_name` metadata
- **Login**: `supabase.auth.signInWithPassword()` → redirects to `/client`
- **Password reset**: `resetPasswordForEmail()` via `authHelpers.ts`
- Both show "Supabase not configured" warning when env vars missing

### Client Portal (`src/pages/client/`)
- `ClientPortalRoot.jsx`: client-side routing, NO auth gate
- `ClientPortalShell.jsx`: journey navigation, Hermes guidance panel
- `ClientPortalPages.jsx`: 10 journey step pages
- **ALL DATA IS MOCK** from `clientPortalData` — no Supabase queries

### App Routing (`src/app/App.tsx`)
- `/goclear*` → public pages (no auth)
- `/client*` → `ClientPortalRoot` (NO auth gate)
- `/update-password` → `UpdatePasswordPage`
- Root → `AuthGate` → `NexusAdminUI` (admin only)

## Critical Findings

### 1. NO AUTH GATE ON `/client` ROUTE
- Any visitor (authenticated or not) can access `/client`
- The `ClientPortalRoot` component has no session check
- After login, redirect to `/client` works, but the page doesn't verify the session
- **Risk**: Unauthenticated users see the client portal (mock data, but still a UX/security gap)

### 2. NO PROFILE CREATION ON SIGNUP
- `supabase.auth.signUp()` creates an auth user only
- No database trigger creates a `client_profiles` row
- No `tenant_memberships` row is created
- After signup, the user has no profile data in the database
- **Risk**: User logs in → redirected to `/client` → sees empty mock data → no real profile

### 3. CLIENT PORTAL IS DEMO-ONLY
- `ClientPortalShell.jsx` imports `clientPortalData` from `../../data/clientPortalData`
- All data (profile, tasks, documents, scores) is hardcoded mock data
- No Supabase queries anywhere in the client portal
- **Risk**: Logged-in users see the same demo data regardless of who they are

### 4. MIGRATION STATUS
- `20260629095450_client_portal_core_tables.sql` is DRAFT (header says "DRAFT ONLY")
- Creates `tenant_memberships`, extends `client_profiles` with portal fields
- Defines RLS policies using `nexus_is_active_admin()` + `tenant_memberships`
- **Status**: NOT APPLIED to production (draft only)

### 5. EMAIL CONFIRMATION
- Supabase default: email confirmation required
- Signup page shows "Check Your Email" after `signUp()` — correct behavior
- Login page does not handle "unconfirmed email" error specifically
- **Status**: Assumed working (Supabase default)

## Table Schema (from migrations)

### `admin_users` (APPLIED)
- `id` uuid PK → references `auth.users(id)`
- `email` text
- `role` text default 'admin'
- `active` boolean default true
- RLS: self-select only

### `client_profiles` (DRAFT migration)
- Base table from `20260629090000_client_workflow_engine.sql`:
  - `id` uuid PK, `workspace_id`, `client_label`, `current_stage`, etc.
- Extended by `20260629095450_client_portal_core_tables.sql`:
  - Adds `external_id`, `tenant_id`, `client_id`, `category`, `title`, `status`, etc.
- **NOT LINKED TO AUTH USERS** — no `user_id` column

### `tenant_memberships` (DRAFT migration)
- `tenant_id` text + `user_id` uuid → composite PK
- `role` text: super_admin | admin | operator | client
- `client_id` text
- Links auth users to tenants/clients
- **NOT CREATED YET** (draft migration)

## Recommendations

1. **Add auth gate to `/client` route** — check session before rendering portal
2. **Create profile bootstrap trigger** — on `auth.users` insert, create `tenant_memberships` row
3. **Connect client portal to Supabase** — replace mock data with real queries
4. **Apply client portal migration** — review and apply `20260629095450`
5. **Add login error handling** — distinguish "unconfirmed email" from wrong password
