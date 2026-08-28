# Nexus / Oracle Hermes Bridge Certification — 2026-08-28

`BRIDGE_IMPLEMENTATION=CREATED`
`BRIDGE_CERTIFICATION=UNIT_LEVEL_ONLY`
`PRIVATE_TRANSPORT=DESIGNED_NOT_CONNECTED`

The Mac-side adapter is `scripts/nexus_agent_platform/bridge/oracle_hermes.py`.
It uses Hermes' official OpenAI-compatible API shape, requires a loopback base
URL and runtime credential, correlates request IDs, rejects obvious PII by
default, validates response shape, and returns explicit
`UNAVAILABLE`/`FAIL_CLOSED` responses for timeout, transport, or malformed
responses. It has no shell, database-write, gate-approval, payment, trading,
credential, or production-mutation capability.

Synthetic unit coverage proves success correlation/advisory labeling, timeout
failure, malformed-response failure, PII denial, and public-endpoint rejection.
Real E2E tests are pending Oracle deployment and private SSH-forward activation.
No Telegram message was sent. `TRUTHKERNEL_READ_ONLY=YES`;
`NEXUS_AUTHORITY_PRESERVED=YES`; `PYTHON_AUTHORITY_PRESERVED=YES`.
