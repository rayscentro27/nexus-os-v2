# Fake Customer Cleanup SQL Packet

Generated: 2026-06-29T23:04:14.883564+00:00

- ok: true
- status: synthetic_cleanup_packet_ready_default_rollback
- packet_path: reports/manual_publish/fake_customer_cleanup_sql_packet_latest.sql
- default_transaction_end: rollback
- cleanup_executed: false
- approval_required: true
- external_action_performed: false

## SQL

```sql
-- SYNTHETIC TEST CLEANUP ONLY. Default behavior rolls back.
begin;
delete from public.payments_status where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.subscription_memberships where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_tasks where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_documents where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_profiles where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
select count(*) as remaining_rows from public.client_profiles where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
rollback;

```
