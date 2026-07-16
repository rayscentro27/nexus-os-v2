-- Enable pilot controls for invited test-mode pilot certification
BEGIN;

UPDATE public.payment_pilot_controls
SET
  invitations_enabled = true,
  test_mode_purchases_enabled = true,
  controlled_live_pilot_enabled = false,
  public_live_enabled = false,
  hidden_pilot_offer_enabled = false,
  emergency_checkout_disabled = false
WHERE id = 'singleton';

COMMIT;
