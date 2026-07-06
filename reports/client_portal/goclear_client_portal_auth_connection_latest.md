# GoClear Client Portal Auth Connection

**Date**: 2026-07-06

---

## Current State

### `/client` Route
- `App.tsx` routes `/client*` → `ClientPortalRoot`
- **NO auth gate** — any visitor can access
- `ClientPortalRoot` uses client-side routing with `normalizePath`
- Default path: `/client/dashboard`

### Client Portal Components
- `ClientPortalShell.jsx`: header, navigation, Hermes guidance panel
- `ClientPortalPages.jsx`: 10 journey step pages
- `clientPortalData.js`: ALL mock data (profile, tasks, documents, scores)

### Data Source
- `clientPortalData` is imported from `../../data/clientPortalData`
- Contains: `clientProfile`, `creditProfile`, `tasks`, `documents`, `readinessScores`, etc.
- **100% hardcoded** — no Supabase queries

## What Logged-In Users See

| Scenario | What They See |
|----------|---------------|
| Login → `/client` | Mock data portal (same for everyone) |
| Direct `/client` visit | Mock data portal (no auth check) |
| After refresh | Mock data portal (session persists but unused) |

## Auth Connection Status

| Component | Auth Connected | Data Source |
|-----------|---------------|-------------|
| GoClear Signup | YES (Supabase signUp) | Auth metadata only |
| GoClear Login | YES (Supabase signIn) | Redirect to /client |
| Client Portal | NO | Mock data |
| Admin Dashboard | YES (AuthGate) | Mock data (NexusAdminUI) |

## Gap: What's Needed

### 1. Auth Gate for `/client`
- Check session before rendering portal
- Redirect to `/goclear/login` if not authenticated
- Show loading state while checking

### 2. Profile Data from Supabase
- Query `client_profiles` or `tenant_memberships` for logged-in user
- Replace mock `clientPortalData` with real data
- Handle "no profile yet" state (new signup)

### 3. User-Specific Content
- Filter tasks/documents/scores by user's `client_id`
- Show only `client_visible = true` items
- Personalize Hermes guidance

### 4. Logout
- Add sign-out button to portal header
- Clear session and redirect to `/goclear/login`

## Recommended Implementation

### Option A: Add Auth Gate Only (Minimal)
1. Add `useSession()` to `ClientPortalRoot`
2. If no session → redirect to `/goclear/login`
3. Keep mock data for now

### Option B: Full Integration (Complete)
1. Add auth gate
2. Query Supabase for user's profile/membership
3. Replace mock data with real queries
4. Add "no profile" onboarding state
5. Add logout button

## Status: NOT CONNECTED

Client portal is demo-only. No auth check, no real data.
