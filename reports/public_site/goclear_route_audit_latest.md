# GoClear Route Audit Report

**Date:** 2026-07-06
**Status:** ROUTING CODE CORRECT — STALE DEPLOYMENT

## App.tsx Route Architecture

No React Router — uses raw `window.location.pathname` matching (pathname-based routing).

### Route Order (src/app/App.tsx:24-46)

1. **GoClear public routes** (no auth):
   - `/goclear` → `GoClearLandingPage`
   - `/goclear/signup` → `GoClearSignupPage`
   - `/goclear/pricing` → `GoClearPricingPage`
   - `/goclear/login` → `GoClearLoginPage`

2. **Internal protected routes**:
   - `/update-password` → `UpdatePasswordPage`
   - `/client/*` → `ClientPortalGate` (redirects to `/goclear/login` if not authenticated)

3. **Dev-only smoke test** (Vite `import.meta.env.DEV` → false in prod):
   - `?ui-smoke=1` → `NexusAdminUI`

4. **Catch-all (default)**:
   - → `AuthGate` → `SignInForm` (admin login)

### Key Findings

- **No catch-all redirect to admin login for public routes.** The `AuthGate` only catches the default case (unknown paths). GoClear routes are defined before it.
- **No React Router `basename` issue.** The app uses direct pathname checks.
- **No Netlify redirect interfering.** The `/* → /index.html` SPA fallback is standard and correct.
- **Route matching hardened:** Added trailing-slash normalization (`replace(/\/+$/, '')`) to handle edge cases.

### AuthGate Behavior (src/components/auth.tsx:106-111)

```tsx
export function AuthGate({ children }) {
  const { user, loading, recoveryMode } = useSession();
  if (loading) return <div>Loading…</div>;
  if (recoveryMode) return <UpdatePasswordForm />;
  if (!user) return <SignInForm />;  // ← This is what shows "Admin sign-in"
  return <>{children(user)}</>;
}
```

`AuthGate` only renders when no GoClear route matches the pathname.

### ClientPortalGate (src/app/App.tsx:14-22)

Redirects unauthenticated users to `/goclear/login`. Auth-protected.

## Conclusion

The routing code is correct. The live issue is caused by a stale Netlify deployment (old JS bundle without GoClear components).
