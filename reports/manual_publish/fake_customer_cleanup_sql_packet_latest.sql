-- SYNTHETIC TEST CLEANUP ONLY. Default behavior rolls back.
begin;
delete from public.payments_status where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.subscription_memberships where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_tasks where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_documents where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
delete from public.client_profiles where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
select count(*) as remaining_rows from public.client_profiles where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
rollback;
