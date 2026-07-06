# GoClear Signup Bootstrap Design

**Date**: 2026-07-06

---

## Goal

When a new GoClear user signs up via `/goclear/signup`, Supabase automatically creates:
1. A `tenant_memberships` row (user → GoClear tenant, role = 'client')
2. A `client_profiles` row (linked to user via `tenant_memberships.client_id`)

## Design: SECURITY DEFINER Trigger on `auth.users` INSERT

### Why Trigger (not Frontend)
- Frontend cannot safely INSERT into `tenant_memberships` (RLS blocks it)
- Frontend cannot be trusted to create the correct tenant/client linkage
- Trigger runs with function owner privileges ( SECURITY DEFINER )
- No service role key needed in frontend
- Idempotent: ON CONFLICT prevents duplicate rows

### Flow
```
User signs up → auth.users row created → trigger fires →
  1. Upsert tenant_memberships (user_id, tenant_id='goclear', role='client', client_id=new_client_id)
  2. Upsert client_profiles (id=new_client_id, tenant_id='goclear', client_label=full_name, ...)
```

### Client ID Generation
- `client_id` = `'gc_' || replace(new.id::text, '-', '')` — deterministic, unique, prefixed
- Same `client_id` used in both `tenant_memberships` and `client_profiles`
- Idempotent: if membership already exists, skip

### Default Tenant
- Tenant ID: `'goclear'` (text, not uuid)
- No separate `tenants` table needed (tenant_id is just a text discriminator)
- If tenant-specific config is needed later, create a `tenants` table then

### Metadata Extraction
- `full_name` from `new.raw_user_meta_data ->> 'full_name'`
- `business_name` from `new.raw_user_meta_data ->> 'business_name'`
- `email` from `new.email`

## Security Model

| Action | Who Can Do It |
|--------|--------------|
| Create auth user | Supabase (signup) |
| Create tenant_membership | Trigger (SECURITY DEFINER) |
| Create client_profile | Trigger (SECURITY DEFINER) |
| Read own membership | Authenticated user (RLS self-select) |
| Read own profile | Authenticated user (RLS self-select via membership) |
| Update own profile fields | Authenticated user (RLS self-update) |
| Create arbitrary memberships | BLOCKED (no self-service INSERT policy) |
| Grant admin role | BLOCKED (trigger hardcodes role='client') |
| Read other users' data | BLOCKED (RLS tenant + client_id match) |

## Idempotency

- `ON CONFLICT (tenant_id, user_id) DO NOTHING` on membership
- `ON CONFLICT (id) DO NOTHING` on profile
- Safe to re-run trigger if auth user already has rows

## Status: READY FOR MIGRATION
