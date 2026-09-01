# Nexus MCP live response attribution

The following claims in the live Telegram responses were not attributable to a
fresh MCP result for the turns where they appeared: Stripe Checkout,
PaymentIntent, fake customer, email mismatch, “no active services”, 8,510,
27, 35, the 62%/$25/$200 candidate, and reviews requiring Ray.

The receipts show these responses used prior/session or model-generated context,
not fresh Nexus MCP output. The current MCP receipts instead report filtered
historical data and truthful empty/current envelopes. This is classified as
`SESSION_CONTEXT_DOMINATES_FRESH_RESULT` combined with
`NO_FRESH_MCP_READ`, not as a new canonical-state defect.
