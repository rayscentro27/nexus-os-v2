# Global Blocker Resolution Matrix

Generated: 2026-06-30T02:24:16.905834+00:00

- ok: true
- status: global_blocker_matrix_ready
- blockers_total: 10
- resolved_or_partially_resolved: 1
- approval_gated: 5
- missing_source: 2
- missing_credential: 2
- external_action_performed: false

## Blockers

- `{"blocker": "Stripe Checkout completion", "cause": "Browser test payment not completed", "fix_attempted": "Test Checkout created and status tracked", "next_action": "Approve manual test Checkout completion", "result": "open_unpaid", "status": "blocked_by_approval"}`
- `{"blocker": "Stripe PaymentIntent confirmation", "cause": "Test payment method not approved", "fix_attempted": "Test intent created and reusable", "next_action": "Approve pm_card_visa test confirmation", "result": "requires_payment_method", "status": "blocked_by_approval"}`
- `{"blocker": "Resend", "cause": "Key/account permission and .cc/.com sender mismatch", "fix_attempted": "Read-only diagnosis and fix packet", "next_action": "Verify goclearonline.com and replace/re-scope key", "result": "HTTP 403", "status": "blocked_by_missing_credential"}`
- `{"blocker": "Persistent fake customer", "cause": "Production write intentionally gated", "fix_attempted": "RLS verified; insert/cleanup packets ready", "next_action": "Approve explicit synthetic insert", "result": "ready_for_Ray_approval", "status": "blocked_by_approval"}`
- `{"blocker": "Frontend live data", "cause": "Fake customer not persistently inserted", "fix_attempted": "Flagged live-read service with fallback", "next_action": "Enable after insert verification", "result": "implementation_ready_flag_off", "status": "blocked_by_approval"}`
- `{"blocker": "YouTube transcript", "cause": "Approved TXT absent", "fix_attempted": "Approved dropzone and import packet", "next_action": "Add zbAmmnMh5ew.txt", "result": "metadata_review_active", "status": "blocked_by_missing_source"}`
- `{"blocker": "NotebookLM import", "cause": "No approved export file", "fix_attempted": "Legacy adapter and dropzone recovered", "next_action": "Add selected notebook export", "result": "zero_sources", "status": "blocked_by_missing_source"}`
- `{"blocker": "Oanda practice verification", "cause": "Practice environment not explicit", "fix_attempted": "Read-only guard and plan", "next_action": "Set OANDA_ENVIRONMENT=practice", "result": "no API call", "status": "blocked_by_missing_credential"}`
- `{"blocker": "Vibe CLI", "cause": "CLI package unidentified", "fix_attempted": "Recovered legacy synthetic backtest", "next_action": "Do not install until trusted package is identified", "result": "50-trade backtest passed", "status": "partially_completed"}`
- `{"blocker": "Permanent schedule", "cause": "Permanent daemon requires approval", "fix_attempted": "Validated launchd install/rollback plan", "next_action": "Approve safe scheduler installation", "result": "not installed", "status": "blocked_by_approval"}`
