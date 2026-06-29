# Synthetic Rollback Transaction Test

Generated: 2026-06-29T20:16:28.128231+00:00

- ok: true
- status: skipped_no_guaranteed_transaction_channel
- test_attempted: false
- rollback_guaranteed: false
- persistent_record_created: false
- database_write_performed: false
- reason: Supabase CLI provides schema inspection but no bounded transaction callback in this environment; a REST insert/delete pair is not equivalent to guaranteed rollback.
- next_required_action: Approve a server-side SQL function or direct transaction harness that always raises/rolls back synthetic test rows.
- external_action_performed: false
