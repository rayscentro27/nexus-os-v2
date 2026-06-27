# Client Vault Contract

- connection_status: not_connected_by_design
- adapter_in_use: mock
- second_supabase_connected: False
- real_client_data_present: False

## Adapter interface
- client_profiles
- credit_report_metadata
- credit_score_snapshots
- business_profile
- business_setup_items
- proof_uploads
- letter_packets
- mailing_records
- workflow_tasks
- reminder_tasks
- funding_readiness_summaries
- affiliate_attribution_events
- consent_events
- audit_events
- sanitized_signal_export

## Data model
- client_profile
- client_credit_report
- client_credit_score_snapshot
- client_business_profile
- client_business_setup_item
- client_proof_upload
- client_letter_packet
- client_mailing_record
- client_workflow_task
- client_reminder_event
- client_funding_readiness_summary
- client_affiliate_attribution_event
- client_consent_event
- client_audit_event

## Future backends
- separate_supabase_project
- separate_schema
- self_hosted_supabase
- plain_postgres_vault
- other_backend
