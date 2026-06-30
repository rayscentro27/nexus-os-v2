# Client Dashboard Live Test Plan

Generated: 2026-06-30T00:07:28.819456+00:00

- ok: true
- status: live_dashboard_test_plan_ready_flag_off
- route: /client/dashboard
- feature_flag: VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT
- enabled: false
- fallback_static_demo_data: true
- service_role_frontend: false
- requires_fake_customer_insert: true
- approval_required: true
- local_enable_command: printf '\nVITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true\n' >> .env.local
- production_enable_command: netlify env:set VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT true
- external_action_performed: false
