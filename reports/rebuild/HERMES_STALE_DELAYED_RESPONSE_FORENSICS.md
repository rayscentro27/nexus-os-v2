# Stale and delayed response forensics

Update 590357275 delivered the stale attention response at 2026-09-01
03:52:36Z (20:52 Phoenix on Aug 31). Its receipt shows no Langfuse trace,
`nexus_read_shadow`, repeated web calls, and Alpha activity. The response
contained historical Stripe, PaymentIntent, account/email, fake-customer,
health, and opportunity claims. This was a pre-current-MCP runtime path, not a
new canonical Nexus truth defect.

Update 590357276 delivered a progress-only response at 13:46:20Z with zero
tools: “Let me check Nexus … [Fetching current status...]”. It was a model
final, not a Telegram progress lifecycle. The repair refuses to deliver such a
response and grants the same Hermes-native invocation one bounded retry.
