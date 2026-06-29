# Post-DB Schema Verification Plan

Generated: 2026-06-29T17:35:27.543997+00:00

- ok: true
- status: plan_ready
- expected_unique_table_count: 31
- expected_new_policy_count: 71
- verify_tables_sql: SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' AND tablename = ANY(<approved expected-table array>) ORDER BY tablename;
- verify_policies_sql: SELECT tablename, policyname, cmd, roles, qual, with_check FROM pg_policies WHERE schemaname='public' AND tablename = ANY(<approved expected-table array>) ORDER BY tablename, policyname;
- safest_fake_client_test: In a separately approved pass, use a transaction with synthetic tenant/client values, verify projected columns, and ROLLBACK. Use dedicated synthetic authenticated users for RLS allow/deny tests.
- external_action_performed: false
