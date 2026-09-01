# Langfuse SDK export API audit

Langfuse 4.14.2 is installed in both the Nexus observability environment and the current Hermes child environment. The supported API is `start_as_current_observation`; the current adapter uses it through `OtelAdapter.span()` and `record_generation()`. Flush uses `Langfuse.flush()`.

The earlier failure was caused by using a human-readable `nova-...` correlation value as if it were a Langfuse trace id and by ignoring the adapter's supplied trace id. The repaired path derives/accepts a valid 32-character lowercase hexadecimal trace id and passes it as `trace_context`.

Export stack: native Langfuse SDK through the existing Nexus-owned OpenTelemetry adapter. No legacy Langfuse API or old Agent Platform execution path is used.
