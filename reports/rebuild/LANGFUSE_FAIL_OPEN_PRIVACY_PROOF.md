# Fail-open and privacy proof

The adapter is optional and fail-open: Langfuse initialization, span creation, export, and flush exceptions are swallowed or logged without changing Hermes, MCP, Web, Alpha, or Telegram execution. No tracing-only LLM call is made.

Existing redaction covers bot tokens, authorization material, API keys, provider tokens, JWTs, payment/service keys, email, phone, SSN, and sensitive metadata keys. Session identifiers in the new local trace path are hashed; no raw session id is written by `NovaTrace`.

Observed diagnostic payloads contained campaign/purpose metadata only. No credentials or client documents were exported. Langfuse remains diagnostic observability, not Nexus business truth or durable business state.
