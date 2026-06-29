# Hermes Connector Activation Brief

Generated: 2026-06-29T18:40:30.954326+00:00

- ok: true
- status: admin_brief_ready
- next_money_action: Approve one Stripe CLI test-mode $97 Checkout, then prove webhook-to-test-client idempotency before persistent insertion.
- external_action_performed: false

## Recommendations

- Stripe CLI test mode is verified. Use it only after Ray approves the synthetic Checkout or PaymentIntent test; never pass --live.
- Keep the synthetic customer package dry-run until a verified test webhook and idempotency proof exist.
- Recover the legacy NotebookLM adapter first; rebuild its isolated CLI only after Ray approval.
- Add one approved TXT transcript to activate transcript review; keep YouTube API metadata and yt-dlp probing separate.
- Require explicit Oanda practice environment proof before any broker test; use existing backtest components without placing orders.
- Keep Stripe first and payment repository concepts roadmap-only.
