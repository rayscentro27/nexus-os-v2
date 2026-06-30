# Revenue Recovery Funnel

Generated: 2026-06-30T13:13:02.929246+00:00

- ok: true
- status: revenue_recovery_funnel_ready
- stages: 8
- active_internal_stages: 3
- external_stages_gated: 5
- external_action_performed: false

## Stages

- `{"stage": "research_source", "status": "active_internal"}`
- `{"stage": "lead_reactivation_draft", "status": "draft_ready"}`
- `{"stage": "Ray_approval", "status": "required"}`
- `{"stage": "Stripe_test_checkout", "status": "open_unpaid"}`
- `{"stage": "payment_confirmation", "status": "approval_gated"}`
- `{"stage": "synthetic_onboarding", "status": "dry_run_ready"}`
- `{"stage": "client_delivery", "status": "blocked_until_synthetic_journey_passes"}`
- `{"stage": "subscription_upgrade", "status": "draft"}`
