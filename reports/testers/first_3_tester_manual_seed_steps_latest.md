# First 3 Tester Manual Seed Steps

**Generated:** 2026-07-07

## Step 1: Create Auth Users in Supabase Dashboard

1. Go to https://supabase.com/dashboard → Select project → Authentication → Users
2. Click "Add User"
3. Create 3 users:
   - Email: `tester01@goclear.test` / Password: `TestPass123!`
   - Email: `tester02@goclear.test` / Password: `TestPass123!`
   - Email: `tester03@goclear.test` / Password: `TestPass123!`
4. Copy each Auth User ID (UUID format)

## Step 2: Create Local-Only Tester File

Create `data/private/first_3_testers.local.json`:

```json
[
  {
    "email": "tester01@goclear.test",
    "auth_user_id": "PASTE_UUID_HERE",
    "display_name": "Tester 01"
  },
  {
    "email": "tester02@goclear.test",
    "auth_user_id": "PASTE_UUID_HERE",
    "display_name": "Tester 02"
  },
  {
    "email": "tester03@goclear.test",
    "auth_user_id": "PASTE_UUID_HERE",
    "display_name": "Tester 03"
  }
]
```

## Step 3: Run Seed Script (Dry-Run First)

```bash
cd ~/nexus-os-v2
python3 scripts/testers/seed_first_3_testers.py --dry-run
```

## Step 4: Apply Seed Script

```bash
export SUPABASE_URL="https://iqjwgpnujbeoyaeuwehj.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
python3 scripts/testers/seed_first_3_testers.py --apply
```

## Step 5: Test Login

1. Visit https://goclearonline.cc/client/login
2. Log in as tester01@goclear.test
3. Confirm dashboard loads with seeded data

## Step 6: Verify Dashboard

- [ ] Name displays correctly
- [ ] Readiness scores show
- [ ] Tasks list shows
- [ ] Document requirements show
- [ ] Hermes guidance shows
- [ ] No admin login visible
- [ ] Mobile layout works

## Important Notes

- `data/private/` is gitignored — no real data committed
- Seed script uses dry-run by default
- Bootstrap trigger auto-creates client_profiles and tenant_memberships on auth user creation
- Seed script adds readiness_scores, tasks, documents, workflow items, guidance
