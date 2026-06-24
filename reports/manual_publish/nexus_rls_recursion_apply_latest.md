# Nexus RLS Recursion Migration Apply Status

Date: 2026-06-24

## Commit push

Pushed commit:

`b1b1ea6ae2a31f294ba170dd81610635bff433fc`

Commit message:

`fix admin users rls recursion`

## Supabase project check

Supabase CLI is installed.

Linked project metadata was present under `supabase/.temp`.

Expected project ref:

`iqjwgpnujbeoyaeuwehj`

Linked project ref:

`iqjwgpnujbeoyaeuwehj`

The refs matched before applying the migration.

## Migration apply

Dry run command:

`supabase db push --dry-run`

Dry run result:

Only this migration would be applied:

`20260624190000_fix_admin_users_rls_recursion.sql`

Apply command used:

`supabase db push`

Apply result:

Migration applied successfully to the linked Supabase project.

Remote migration list now includes:

`20260624190000`

## Verification

Safe checks after migration:

- `approval_13eafcab_status=pending`
- Facebook account `131069194210954` still has `publish_enabled=False`
- `npm run build` passed
- `npm run nexus:watch` passed

## Expected live UI result

After refreshing or signing back into `https://nexusv20.netlify.app`, the Approvals diagnostics should no longer show `infinite recursion detected in policy for relation "admin_users"`.

Expected:

- Supabase configured: yes
- Auth session: yes
- User: `goclearonline@gmail.com`
- Admin mapping found: yes
- Approvals query should return records
- Pending approval `13eafcab-6940-4612-8239-54786e8c9e60` should appear

## Safety confirmations

- No Facebook approval was changed.
- `publish_enabled` remains false.
- No social post was published.
- No email was sent.
- No trade was placed.
- Scheduler was not started.
- No secrets were printed.
- No service-role key was exposed to frontend code.
