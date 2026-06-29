# Fake Customer Insert SQL Packet

Generated: 2026-06-29T23:04:14.710945+00:00

- ok: true
- status: synthetic_insert_packet_ready_default_rollback
- packet_path: reports/manual_publish/fake_customer_insert_sql_packet_latest.sql
- test_mode: true
- default_transaction_end: rollback
- persistent_insert_performed: false
- approval_required_before_commit: true
- external_action_performed: false

## SQL

```sql
-- SYNTHETIC TEST ONLY. Default behavior rolls back; do not change to COMMIT without Ray approval.
begin;
insert into public.client_profiles (external_id,tenant_id,client_id,category,title,summary,status,client_visible,approval_required,source,payload)
values ('client_test_julius_erving','tenant_test_goclear','client_test_julius_erving','client_profile','Julius Erving','Synthetic test customer: Doctor J LLC, delivery driver, AZ','test_pending',false,true,'manual_test_customer','{"test_mode":true,"do_not_contact":true,"do_not_charge":true,"email":"ray@goclearonline.com","primary_goal":"all"}'::jsonb)
on conflict (tenant_id,external_id) where external_id is not null do update set payload=excluded.payload, updated_at=now();
insert into public.subscription_memberships (id,tenant_id,client_id,category,title,status,client_visible,approval_required,payload)
values ('membership_test_julius_97','tenant_test_goclear','client_test_julius_erving','subscription_membership','$97 readiness review','test_not_paid',false,true,'{"test_mode":true,"amount_cents":9700}'::jsonb)
on conflict (id) do update set status=excluded.status, updated_at=now();
insert into public.payments_status (id,tenant_id,client_id,category,title,status,client_visible,approval_required,payload)
values ('payment_test_julius_97','tenant_test_goclear','client_test_julius_erving','payment_status','Stripe test payment','test_open_unpaid',false,true,'{"test_mode":true,"do_not_charge":true}'::jsonb)
on conflict (id) do update set status=excluded.status, updated_at=now();
select tenant_id,client_id,status from public.client_profiles where tenant_id='tenant_test_goclear' and client_id='client_test_julius_erving';
rollback;

```
