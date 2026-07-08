# Tester Seed Plan

**Generated:** 2026-07-07

## Approach

Create 10 tester accounts with placeholder data for manual testing.

## Steps

### Option A: Manual Creation (Recommended for First Testers)

1. Go to Supabase Dashboard → Authentication → Users
2. Create 10 test users with emails like `tester1@goclear.test`, `tester2@goclear.test`, etc.
3. Use the bootstrap trigger (migration 20260706120000) — it auto-creates:
   - `client_profiles` row
   - `tenant_memberships` row
4. After user creation, manually update `client_profiles`:
   - Set `title` to tester name
   - Set `status` to 'active'
   - Set `client_visible` to true
   - Set `payload` with membership info

### Option B: Script-Based (Dry-Run by Default)

- Script: `scripts/testers/seed_test_client_template.py`
- Creates placeholder users in Supabase Auth
- Links to client_profiles via bootstrap trigger
- Requires explicit `--write` flag to execute
- Never prints secrets
- Never commits real data

## Required Fields Per Tester

| Field | Source | Notes |
|-------|--------|-------|
| email | Test email | Must be unique |
| password | Placeholder | Must be changed on first login |
| name | Test name | Can be fake |
| tenant_id | 'goclear' | Fixed |
| role | 'client' | Fixed |
| status | 'active' | After profile created |

## Data That Must Never Go in Git

- Real tester emails
- Real tester personal information
- Real credit report data
- Real bank statements
- Real ID documents

## Manual Fallback

If auth seeding is not ready:
1. Create users via Supabase Dashboard
2. Run SQL to create profiles:
   ```sql
   INSERT INTO client_profiles (tenant_id, client_id, title, status, client_visible)
   VALUES ('goclear', 'gc_<user_id_no_dashes>', 'Test User', 'active', true);
   ```
3. Create membership:
   ```sql
   INSERT INTO tenant_memberships (tenant_id, user_id, role, client_id)
   VALUES ('goclear', '<user_id>', 'client', 'gc_<user_id_no_dashes>');
   ```
