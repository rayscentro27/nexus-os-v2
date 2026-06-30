# Stripe Manual Test Completion Packet

Generated: 2026-06-30T13:13:08.198471+00:00

- ok: true
- status: manual_test_completion_approval_required
- checkout_status: test_checkout_session_reused_open_not_completed
- checkout_completed: false
- payment_intent_status: requires_payment_method
- payment_intent_confirmed: false
- local_checkout_url_retrieval_command: python3 -c 'import json; print(json.load(open(".stripe_test_runtime/stripe_test_objects_latest.local.json"))["checkout"]["url"])'
- payment_intent_confirmation_command_template: stripe payment_intents confirm <LOCAL_TEST_PI_ID> --payment-method pm_card_visa
- raw_checkout_url_included: false
- raw_payment_id_included: false
- real_charge_made: false
- approval_cards_created: 2
- external_action_performed: false

## Approval cards

- `{"approval_required": true, "created_at": "2026-06-30T13:13:08.197784+00:00", "exact_action": "Retrieve the gitignored URL locally and complete with Stripe test card 4242 4242 4242 4242.", "external_action_performed": false, "id": "approve-manual-test-checkout", "status": "pending_Ray_review", "test_mode_only": true, "title": "Approve manual completion of Stripe test Checkout Session"}`
- `{"approval_required": true, "created_at": "2026-06-30T13:13:08.198042+00:00", "exact_action": "Attach pm_card_visa and confirm only after re-verifying livemode=false.", "external_action_performed": false, "id": "approve-test-intent-confirm", "status": "pending_Ray_review", "test_mode_only": true, "title": "Approve Stripe test PaymentIntent confirmation using test payment method"}`
