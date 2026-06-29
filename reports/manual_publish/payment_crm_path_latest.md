# Payment / CRM Path

Generated: 2026-06-29T16:39:09.626035+00:00

- ok: true
- status: configuration_found_approval_pending
- raw_values_included: false
- stripe_configuration_detected: true
- crm_configuration_detected: false
- live_payment_link_created: false
- money_charged: false
- crm_next_step: Use Supabase client_profiles as initial CRM system of record
- ray_review_card: Approve payment provider, $97 scope, test-mode checkout, and post-payment client creation workflow.
- external_action_performed: false
- summary: Payment keys were safely checked and a complete $97 onboarding path was prepared without charging or creating a live link.

## Manual fallback

- Ray selects an approved payment method
- operator verifies status manually
- create tenant-scoped client only after verified payment
- log proof event

## Stripe checklist

- verify server-side secret and publishable key pairing
- create/confirm $97 product and price
- configure webhook signature secret
- map paid event to idempotent client creation
- test in Stripe test mode
- Ray approves production switch

## Onboarding

- `{"approval_required": true, "automation_level": "admin_review_required", "category": "post_payment_onboarding", "client_id": "client_pending_creation", "client_visible": false, "created_at": "2026-06-29T16:39:09.622746+00:00", "id": "onboarding-1", "priority": "high", "risk_level": "low", "status": "template_ready", "tenant_id": "tenant_demo_goclear", "title": "Verify approved payment status"}`
- `{"approval_required": true, "automation_level": "admin_review_required", "category": "post_payment_onboarding", "client_id": "client_pending_creation", "client_visible": false, "created_at": "2026-06-29T16:39:09.622761+00:00", "id": "onboarding-2", "priority": "high", "risk_level": "low", "status": "template_ready", "tenant_id": "tenant_demo_goclear", "title": "Create tenant-scoped client profile"}`
- `{"approval_required": true, "automation_level": "admin_review_required", "category": "post_payment_onboarding", "client_id": "client_pending_creation", "client_visible": false, "created_at": "2026-06-29T16:39:09.622769+00:00", "id": "onboarding-3", "priority": "high", "risk_level": "low", "status": "template_ready", "tenant_id": "tenant_demo_goclear", "title": "Assign $97 review workflow"}`
- `{"approval_required": true, "automation_level": "admin_review_required", "category": "post_payment_onboarding", "client_id": "client_pending_creation", "client_visible": false, "created_at": "2026-06-29T16:39:09.622776+00:00", "id": "onboarding-4", "priority": "high", "risk_level": "low", "status": "template_ready", "tenant_id": "tenant_demo_goclear", "title": "Request minimum documents with consent"}`
- `{"approval_required": true, "automation_level": "admin_review_required", "category": "post_payment_onboarding", "client_id": "client_pending_creation", "client_visible": false, "created_at": "2026-06-29T16:39:09.622783+00:00", "id": "onboarding-5", "priority": "high", "risk_level": "low", "status": "template_ready", "tenant_id": "tenant_demo_goclear", "title": "Schedule GoClear manual review"}`
- `{"approval_required": true, "automation_level": "admin_review_required", "category": "post_payment_onboarding", "client_id": "client_pending_creation", "client_visible": false, "created_at": "2026-06-29T16:39:09.622791+00:00", "id": "onboarding-6", "priority": "high", "risk_level": "low", "status": "template_ready", "tenant_id": "tenant_demo_goclear", "title": "Publish approved tasks to client portal"}`
