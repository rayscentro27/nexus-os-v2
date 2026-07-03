# Future Oanda Demo Execution Plan

Future only; no connection or trade in this phase. Use Oanda fxTrade Practice endpoint only after explicit approval. Live/funded endpoints remain blocked.

Proposed starting policy (Ray must approve): allowlist `EUR_USD`, `GBP_USD`, `USD_JPY`; maximum 1,000 units/order; 1 open trade; 2 trades/day; daily demo realized+unrealized loss limit $25; no weekend/illiquid-session entry unless strategy specifies it. Every order needs strategy ID/version, reason, risk rule, stop loss or deterministic exit, position-size calculation, spread check, and approval receipt.

Kill switch triggers: environment mismatch, missing receipt fields, daily limit, stale pricing, unexpected open position/order, repeated rejection, strategy/version mismatch, missing stop/exit, credential error, or operator command. Kill switch blocks new orders and creates a review report; it never attempts recovery trading.

Required controls: practice-host allowlist, account-mode verification per request, credential isolation, idempotency, max-unit clamp, open-position reconciliation, transaction receipt, daily ledger, no martingale/pyramiding/revenge loops, no recursive retry, and no performance claim based solely on demo fills.

Activation sequence: offline backtests → paper simulator → policy tests → read-only practice account/instrument/pricing checks → Ray-approved one-shot dry run → Ray-approved smallest practice order → reconciliation/receipt review. No scheduler until multiple manual receipts pass.
