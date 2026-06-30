# Webhook-to-Customer Onboarding Dry Run

Generated: 2026-06-30T00:07:02.489803+00:00

- ok: true
- status: webhook_events_mapped_to_onboarding_dry_run
- records_created: 3
- persistent_database_insert: false
- auth_user_created: false
- email_sent: false
- real_charge_made: false
- external_action_performed: false

## Records

- `{"category": "webhook_onboarding_dry_run", "client_id": "client_test_julius_erving", "created_at": "2026-06-30T00:07:02.488692+00:00", "database_inserted": false, "do_not_charge": true, "do_not_contact": true, "dry_run": true, "email_sent": false, "id": "webhook-dry-1", "status": "mapped_test_event_not_persisted", "tenant_id": "tenant_test_goclear", "test_mode": true, "title": "checkout.session.completed"}`
- `{"category": "webhook_onboarding_dry_run", "client_id": "client_test_julius_erving", "created_at": "2026-06-30T00:07:02.489013+00:00", "database_inserted": false, "do_not_charge": true, "do_not_contact": true, "dry_run": true, "email_sent": false, "id": "webhook-dry-2", "status": "mapped_test_event_not_persisted", "tenant_id": "tenant_test_goclear", "test_mode": true, "title": "payment_intent.payment_failed"}`
- `{"category": "webhook_onboarding_dry_run", "client_id": "client_test_julius_erving", "created_at": "2026-06-30T00:07:02.489027+00:00", "database_inserted": false, "do_not_charge": true, "do_not_contact": true, "dry_run": true, "email_sent": false, "id": "webhook-dry-3", "status": "mapped_test_event_not_persisted", "tenant_id": "tenant_test_goclear", "test_mode": true, "title": "payment_intent.succeeded"}`
