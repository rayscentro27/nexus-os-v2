# Supabase Migration Truth

Date: 2026-07-17
Supabase CLI: 2.90.0

## Commands

```bash
supabase --version
supabase status --workdir supabase
supabase projects list
supabase migration list
```

## Results

`supabase status --workdir supabase`:

- Exit code: 1.
- Blocker: Docker daemon is not running locally.
- Meaning: local Supabase container health could not be inspected.

`supabase projects list`:

- Exit code: 0.
- Linked project detected: `nexus-os-v2`.
- Reference ID was visible in CLI output but is not operationally sensitive; no secrets were printed.

`supabase migration list`:

- Exit code: 0.
- Remote database connection succeeded.
- `DRAFT_client_portal_core_tables.sql` skipped because filename does not match migration naming pattern.

## Migration Classification

Aligned local and remote:

- `0001` through `0011`
- `20260624190000`
- `20260629090000`
- `20260629095450`
- `20260706120000`
- `20260707120000`
- `20260707140000`
- `20260708120000`
- `20260709120000`
- `20260710090000`
- `20260713120000`
- `20260714120000`
- `20260715120000`
- `20260715130000`
- `20260715140000`
- `20260715150000`
- `20260715151000`
- `20260715152000`
- `20260715160000`
- `20260715170000`
- `20260715180000`
- `20260716100000`

Local only:

- `20260715200000_tester_invitation_system.sql`
- `20260716120000_enable_pilot_controls.sql`

Skipped local draft:

- `DRAFT_client_portal_core_tables.sql`

Unknown/conflicting:

- None beyond the two local-only migrations listed above.

## Decision

No migration was applied. No `supabase db push` was run.

Migration Truth Gate: PASS WITH REQUIRED FOLLOW-UP.

Follow-up:

- Decide whether the two local-only tester invitation/pilot migrations should be applied in a separately approved migration sprint.
- They were not required for the Wave 0 customer/auth/RLS/parser certification that passed.
