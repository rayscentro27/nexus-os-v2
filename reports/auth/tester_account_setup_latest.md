# Tester Account Setup — Readiness Report

**Date:** 2026-07-07

## Supabase Auth Status

- **Available:** Yes — Supabase auth is configured and functional
- **Client login URL:** `https://goclearonline.cc/client/login`
- **Auth method:** Email + password (Supabase Auth)
- **Session persistence:** Enabled (auto-refresh token)

## Client Profile Table

- **Exists:** Yes — `client_profiles` table exists in Supabase
- **Auto-creation:** SECURITY DEFINER trigger on `auth.users INSERT` auto-creates:
  - `tenant_memberships` row (tenant = 'goclear')
  - `client_profiles` row (client_id = 'gc_' + user_id without dashes)
- **Default tenant:** `goclear`

## Tester Account Creation — Manual Steps

1. Go to **Supabase Dashboard** → **Authentication** → **Users** → **Add User**
2. Enter email and password (use strong password)
3. Check **Auto Confirm Email** to skip email verification
4. After creation, the trigger auto-creates the membership and profile rows
5. Share the login URL: `https://goclearonline.cc/client/login`
6. Share credentials via secure channel (not email)

## What Data Needs to Be Added Per Tester

The trigger creates a minimal profile. For meaningful tester experience, consider adding:

| Field | Source | Notes |
|-------|--------|-------|
| Full name | Auto from signup metadata | Or update via Supabase dashboard |
| Business name | Optional at signup | Can be added later |
| Credit score | Manual | Not connected to real bureau |
| Funding readiness | Manual | Set via admin or client portal |
| Documents | Manual upload | Client portal document flow |

## Tester Routes

| Route | Purpose |
|-------|---------|
| `https://goclearonline.cc/client/login` | Tester login |
| `https://goclearonline.cc/client/dashboard` | Main dashboard (post-login) |

## Ray Preview Route

| Route | Purpose |
|-------|---------|
| `https://goclearonline.cc/client/preview` | Demo/mock data, no login required |

## What Remains Before Inviting 10 Testers

- [ ] Create tester accounts in Supabase Auth dashboard
- [ ] Test login flow end-to-end
- [ ] Verify client portal renders correctly for new accounts
- [ ] Add sample data to tester profiles (credit score, funding status)
- [ ] Test document upload flow
- [ ] Prepare tester onboarding message with login URL + instructions
- [ ] Set up feedback collection channel
