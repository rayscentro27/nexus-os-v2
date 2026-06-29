# Hermes Connector Activation Brief

Generated: 2026-06-29T18:33:28.584473+00:00

- ok: true
- status: admin_brief_ready
- next_money_action: Configure Stripe test-mode credentials, approve the synthetic $97 Checkout test, then prove webhook-to-test-client idempotency.
- external_action_performed: false

## Recommendations

- Do not use the detected live Stripe keys for testing; configure separate test-mode keys before Checkout or PaymentIntent execution.
- Keep the synthetic customer package dry-run until a verified test webhook and idempotency proof exist.
- Recover the legacy NotebookLM adapter first; rebuild its isolated CLI only after Ray approval.
- Add one approved TXT transcript to activate transcript review; keep YouTube API metadata and yt-dlp probing separate.
- Require explicit Oanda practice environment proof before any broker test; use existing backtest components without placing orders.
- Keep Stripe first and payment repository concepts roadmap-only.
