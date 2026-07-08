# Client Access Routes — Report

**Date:** 2026-07-07

## Final Route Map

| Route | Behavior | Auth Required |
|-------|----------|---------------|
| `/` | GoClear landing page (public) | No |
| `/client/login` | Client portal login (GoClear-branded) | No |
| `/client` | Client portal (redirects to `/client/login` if unauthenticated) | Yes |
| `/client/dashboard` | Client portal dashboard (redirects to `/client/login` if unauthenticated) | Yes |
| `/client/preview` | Client portal with demo/mock data, no auth required, demo banner | No |
| `/admin` | Admin login (AuthGate → SignInForm) | Yes |
| `/admin/command-center` | Admin command center (AuthGate → NexusAdminUI) | Yes |
| `/goclear/login` | GoClear client login (legacy, still works) | No |
| `/goclear/signup` | GoClear signup | No |
| `/goclear/pricing` | GoClear pricing | No |

## Auth Notes

- **Client auth:** `useSession()` hook checks Supabase session → redirects to `/client/login` if unauthenticated
- **Admin auth:** `AuthGate` component checks Supabase session → shows admin `SignInForm` if unauthenticated
- **No role system:** Single Supabase auth session — any authenticated user can access both client and admin routes
- **Client login page:** Dedicated `ClientLoginPage` component with "Client Portal Login" branding
- **Admin login page:** `SignInForm` component with "Nexus OS v2" / "Admin sign-in" branding

## Demo/Mock Data Notes

- **`/client/preview`** uses `clientPortalData` (mock data) — shows demo banner
- **`/client/dashboard`** uses `clientPortalData` (mock data) — behind auth gate
- **Client portal** is not connected to live Supabase queries for credit/funding data
- **No claims of live data** in any client-facing route

## Remaining Blockers

- No role-based access control (any authenticated user = full access)
- Client portal uses mock data, not live Supabase queries
- No real credit bureau connection
- No live funding approval
- No real payment processing
- Tester accounts need manual creation in Supabase dashboard
