# Client Dashboard Live-Data Flag

Generated: 2026-06-30T00:07:28.675132+00:00

- ok: true
- status: live_read_path_implemented_flag_off
- route: /client/dashboard
- feature_flag: VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT
- feature_flag_default: false
- authenticated_supabase_client_only: true
- service_role_frontend: false
- static_fallback_preserved: true
- external_action_performed: false

## Test plan

- Insert approved synthetic test rows
- Create tenant_memberships row for authenticated test user
- Run SQL Editor RLS verification
- Set feature flag in local/preview environment
- Authenticate and verify only the fake customer is visible
- Unset flag to roll back

## Approval

- `{"approval_required": true, "created_at": "2026-06-30T00:07:28.674277+00:00", "default_enabled": false, "external_action_performed": false, "feature_flag": "VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT", "id": "approve-client-dashboard-live-test-read", "status": "pending_Ray_review", "title": "Approve /client/dashboard live Supabase read for fake customer"}`
