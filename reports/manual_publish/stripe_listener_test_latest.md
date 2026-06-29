# Stripe Listener Test

Generated: 2026-06-29T23:01:29.701161+00:00

- ok: true
- status: bounded_test_listener_and_triggers_passed
- bounded: true
- test_mode_verified: true
- listener_started: true
- server_started: true
- signing_secret_available: true
- signing_secret_printed: false
- events_received_count: 4
- listener_stopped: true
- server_stopped: true
- live_mode_used: false
- real_charge_made: false
- external_action_performed: true

## Trigger results

- `{"event_type": "checkout.session.completed", "exit_code": 0, "trigger_succeeded": true}`
- `{"event_type": "payment_intent.succeeded", "exit_code": 0, "trigger_succeeded": true}`
- `{"event_type": "payment_intent.payment_failed", "exit_code": 0, "trigger_succeeded": true}`

## Accepted event types

- checkout.session.completed
- payment_intent.payment_failed
- payment_intent.succeeded
