# Admin Access Connection Map — Nexus OS v2

## Route Guard Architecture

### App-Level Route Resolution
- **File**: `src/app/App.tsx`
- **Mechanism**: Custom client-side router via `window.location.pathname`
- **Admin detection**: `const isAdmin = path === '/admin' || path.startsWith('/admin/')`

### Admin Guard Stack
```
/admin/*
  → AdminGuard (src/components/auth/AdminGuard.tsx)
    → checkAdminAccess() (src/lib/adminAccess.ts)
      → admin_users lookup (active = true)
      → tenant_memberships role lookup (super_admin, admin, operator, owner)
    → AuthGate (src/components/auth.tsx)
      → useSession()
      → SignInForm if no session
    → NexusAdminUI
```

### Client Route Guard Stack
```
/client/*
  → ClientPortalGate (inline in App.tsx)
    → useSession()
    → Redirect to /client/login if no session
    → ClientPortalRoot
      → ClientPortalShell
        → Page components
```

## Admin Role Sources

### Source 1: admin_users
- **Table**: `public.admin_users`
- **Columns**: `id` (uuid, FK to `auth.users`), `email`, `role`, `active`, `created_at`
- **Policy**: `admin_users_select_self` — users can read their own row
- **Function**: `nexus_is_active_admin()` — SECURITY DEFINER, checks `admin_users.id = auth.uid() AND active = true`
- **Frontend check**: `adminAccess.ts` queries `admin_users` first
- **RLS impact**: `nexus_is_active_admin()` gates all admin dashboard table policies

### Source 2: tenant_memberships
- **Table**: `public.tenant_memberships`
- **Columns**: `tenant_id`, `user_id` (uuid, FK to `auth.users`), `role`, `client_id`, `created_at`
- **Role CHECK**: `('super_admin','admin','operator','client')`
- **Policies**:
  - `memberships_self_or_admin_select` — users read own row or admin reads all
  - `memberships_admin_manage` — admin manages all
- **Frontend check**: `adminAccess.ts` queries `tenant_memberships` as fallback if no `admin_users` row
- **Note**: Frontend checks for `'owner'` role, which is NOT in the database CHECK constraint

## Current Admin Guard Implementation

### Frontend Guard
- **File**: `src/lib/adminAccess.ts`
- **Function**: `checkAdminAccess()`
- **Returns**: `{ allowed, source, role, reason }`
- **Logic**:
  1. Query `admin_users` where `id = user.id` and `active !== false`
  2. If found → allowed, source = `admin_users`
  3. Else query `tenant_memberships` where `user_id = user.id` and role in `['super_admin', 'admin', 'operator', 'owner']`
  4. If found → allowed, source = `tenant_memberships`
  5. Else → denied, source = `none`

### Backend RLS
- **Function**: `public.nexus_is_active_admin()`
- **Logic**: `SELECT EXISTS (SELECT 1 FROM public.admin_users WHERE id = auth.uid() AND active = true)`
- **Grants**: `EXECUTE` to `authenticated`; revoked from `public`

## Client/Test User Blocker Logic

### How Clients Are Blocked from Admin
1. Client signs in → `AuthGate` provides user to `AdminGuard`
2. `AdminGuard` calls `checkAdminAccess()`
3. `checkAdminAccess()` queries `admin_users` — client has no row → not found
4. `checkAdminAccess()` queries `tenant_memberships` — client has `role = 'client'` → not in allowed roles
5. Result: `allowed = false`, reason = "No admin access found..."
6. `AdminGuard` renders "Admin access required" with link to `/client/dashboard`
7. `NexusAdminUI` never mounts

### How Ray/Admin Is Identified
1. Ray signs in → `AuthGate` provides user
2. `checkAdminAccess()` queries `admin_users` — finds Ray's row with `active = true`
3. Result: `allowed = true`, source = `admin_users`
4. `AdminGuard` renders `children(access)` → `NexusAdminUI` mounts

## Admin Panels and Their Guards

| Panel | Component | Admin Guarded | Data Source | Client Accessible |
|-------|-----------|---------------|-------------|-------------------|
| Command Center | `NexusAdminUI.jsx` / `sections.tsx` | YES (via AdminGuard) | Live Supabase + bundled JSON | NO |
| Clients | `ClientsPanel.jsx` | YES (via AdminGuard) | Static + live Supabase | NO |
| Credit & Funding | `NexusAdminUI.jsx` | YES | Static + live | NO |
| Readiness Intake | `ReadinessReviewIntake.jsx` | YES | Local state only | NO |
| Readiness Review | `ReadinessReviewAdmin.jsx` | YES | Prop-driven | NO |
| Business Opportunities | `NexusAdminUI.jsx` | YES | Live Supabase | NO |
| Research Engine | `NexusAdminUI.jsx` | YES | Live Supabase | NO |
| Monetization | `NexusAdminUI.jsx` | YES | Live Supabase | NO |
| Marketing Drafts | `NexusAdminUI.jsx` | YES | Live Supabase | NO |
| Trading Demo | `NexusAdminUI.jsx` | YES | Live Supabase | NO |
| Automation Scheduler | `NexusAdminUI.jsx` | YES | Live Supabase | NO |
| CLI/Tool Registry | `NexusAdminUI.jsx` | YES | Live Supabase | NO |
| Settings | `NexusAdminUI.jsx` | YES | Local state | NO |
| Hermes Advisor | `NexusAdminUI.jsx` | YES | Live Supabase | NO |
| GoClear/Apex | `NexusAdminUI.jsx` | YES | Live + static | NO |
| Hermes Alpha | `NexusAdminUI.jsx` | YES | Local state | NO |

## SQL Verification Queries

### Check tester role
```sql
SELECT
  tm.tenant_id,
  tm.client_id,
  tm.role,
  au.email
FROM public.tenant_memberships tm
LEFT JOIN auth.users au ON au.id = tm.user_id
WHERE lower(au.email) = lower('theworldzmine@gmail.com');
```

### Check admin_users entries
```sql
SELECT id, email, role, active, created_at
FROM public.admin_users
ORDER BY created_at DESC
LIMIT 20;
```

### Check if tester is in admin_users
```sql
SELECT au.email, a.*
FROM public.admin_users a
LEFT JOIN auth.users au ON au.id = a.user_id
WHERE lower(au.email) = lower('theworldzmine@gmail.com');
```

### Check Ray/admin accounts
```sql
SELECT id, email, role, active, created_at
FROM public.admin_users
WHERE lower(email) IN (
  'rayscentro@yahoo.com',
  'ray@onechoiceaz.com',
  'ray.davis@tekletics.com'
);
```

## Current Security Status

| Check | Status |
|-------|--------|
| Admin routes wrapped in AdminGuard | YES |
| AdminGuard checks admin_users | YES |
| AdminGuard checks tenant_memberships | YES |
| Frontend does not treat authenticated as admin | YES |
| No service-role key in frontend | YES |
| RLS not bypassed | YES |
| `nexus_is_active_admin()` used in RLS | YES |
| Client routes separated from admin routes | YES |
| `/client/*` requires auth | YES |
| `/admin/*` requires admin role | YES |

## Known Gaps

1. **Frontend `owner` role**: `adminAccess.ts` checks for `'owner'` role, but the database CHECK constraint does not include `'owner'`. A user with `role = 'owner'` in `tenant_memberships` would pass frontend check but fail backend RLS.
2. **Dev smoke bypass**: `import.meta.env.DEV && ui-smoke=1` bypasses admin guard — acceptable for local dev only.
3. **Client can read `admin_users` self-row**: RLS allows authenticated users to read their own `admin_users` row. This is safe but could leak admin existence.
