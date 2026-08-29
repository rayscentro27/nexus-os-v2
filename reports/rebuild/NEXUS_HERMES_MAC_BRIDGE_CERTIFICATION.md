# Hermes Mac Bridge Certification — 2026-08-29

`MAC_PRIVATE_TUNNEL=PASS` and `NEXUS_MAC_BRIDGE=PASS`.

The launchd-managed SSH forward binds only on Mac loopback
`127.0.0.1:18642` and forwards to Oracle loopback `127.0.0.1:8642`. Hermes
itself remains unreachable through a public interface. The protected API key
is stored outside Git in a mode-0600 local file; its value is never recorded.

The existing `OracleHermesBridge` adapter completed a real synthetic request
with request-id generation, authenticated response receipt, advisory-only
warning preservation, and fail-closed error handling. The request context was
synthetic and PII-free. No TruthKernel write, human-gate approval, external
message, payment, trade, or production mutation occurred.

The first 30-second request timed out and correctly returned `UNAVAILABLE`; a
bounded 120-second retry succeeded. This is recorded as verified timeout
handling, not hidden as success.
