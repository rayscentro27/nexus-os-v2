# Canonical Continuation Routing

The prior failure occurred because `continue VOICE-001` entered the
Product Evolution mission/release resolver before the existing governed repair
was identified. The explicit repair ID is now resolved first against persisted
repair state and its owning work order.

VOICE-001 remains linked to work order
`wo_b5a3b90892804ec79164159997caf264`, manual run
`MANUAL-E2E-20260827-2992`, and its existing approval. Current repair state is
`WAITING_WORKER`; deployment remains separately approval-gated.

The resolver precedence is repair, work order, active repair context, mission,
release, workflow context, fuzzy intent, then normal conversation. Unknown
explicit repair IDs are rejected without creating a new object. Product
Evolution continues to handle messages without an explicit governed object.

No repair, work order, mission, release, deployment, email, social action,
payment, or trading action was created or performed.
