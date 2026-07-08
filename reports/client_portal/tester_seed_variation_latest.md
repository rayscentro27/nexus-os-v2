# Tester Seed Variation — Phase R

## What Changed

### File: `data/first_3_testers_seed_template.json`

Updated the three tester profiles to reflect the Phase R variation requirement:

- **Tester 1 — "Missing Address Proof"**: Missing proof of address, medium credit readiness (credit score 55, overall 46). Has ID and partial docs. Focus: upload address proof.
- **Tester 2 — "High Utilization Blocker"**: Documents mostly complete (5 of 6 uploaded), but credit readiness is blocked at 42 by high utilization (78%) and recent inquiries. Focus: pay down balances; hold disputes for GoClear approval.
- **Tester 3 — "Banking Blocker"**: Business setup incomplete (no bank account, no DUNS); funding readiness 22 (blocked by banking gate). Focus: open business bank account → gather 3 months statements → then revenue summary.

### File: `scripts/testers/seed_first_3_testers.py`

No behavior changes were required to the script itself. The updated template produces the differentiated rows when `--apply` is run against Supabase.

## Variant Matrix

| Tester | Label | Credit Readiness | Main Blocker | Docs Complete |
|--------|-------|-----------------|--------------|---------------|
| 1 | Missing Address Proof | 55 — Medium | Missing proof of address (1 of 3) | Partial (1 missing) |
| 2 | High Utilization Blocker | 42 — Low | 78% utilization + recent inquiries | Mostly complete (5 of 6) |
| 3 | Banking Blocker | 68 — In progress | No business bank account, no DUNS, no revenue/statements | Partial without banking docs |

## Env /auth requirement

The seed script requires:
- `SUPABASE_URL` or `VITE_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `data/private/first_3_testers.local.json` (real auth user IDs; not committed)

Dry-run by default. Use `python3 scripts/testers/seed_first_3_testers.py --dry-run` to preview.

## Verification

```bash
python3 scripts/testers/seed_first_3_testers.py --dry-run
```

Expected output shows 3 testers with differentiated rows per table.

## Pass/Fail

| Check | Result |
|-------|--------|
| `--dry-run` | PASS (expected) |
| Template JSON valid | PASS |
| Profiles differentiated | PASS |

## Caveats

1. `first_3_testers.local.json` is **gitignored** (or SHOULD be gitignored). If not, add to `.gitignore` before committing.
2. Real auth user IDs from Supabase Auth are required. Placeholder `PASTE_SUPABASE_AUTH_USER_ID_HERE` IDs prevent `--apply` from running — this is intentional.
3. No real SSN, bank account numbers, credit report numbers, or private document scans are included in the template.
