# First 3 Auth User Login Flow

**Generated:** 2026-07-07

## Auth Users Created

| Tester | Email | Status |
|--------|-------|--------|
| 1 | ray@onechoiceaz.com | ✓ Created |
| 2 | theworldzmine@gmail.com | ✓ Created |
| 3 | ray.davis@tekletics.com | ✓ Created |

## Client Records Seeded

| Table | Rows Created |
|-------|-------------|
| tenant_memberships | 3 |
| client_profiles | 3 |
| readiness_scores | 9 |
| client_tasks | 9 |
| client_documents | 9 |
| credit_workflow_items | 9 |
| business_profile_requirements | 15 |
| approved_client_guidance | 9 |

## Login Flow

1. Visit https://goclearonline.cc/client/login
2. Enter tester email + password
3. Redirects to /client/dashboard
4. Dashboard loads profile from client_profiles
5. Tasks, documents, scores load from respective tables
6. Hermes guidance displays based on status

## Notes

- Auth users created with email_confirm=true (instant login)
- Bootstrap trigger auto-creates profiles on first login
- Seed script added starter data for all 8 tables
