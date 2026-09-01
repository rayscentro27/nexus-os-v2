# Langfuse live connection certification

Campaign: HG-WP6.6-LANGFUSE-LIVE-CONNECTION-AND-E2E-TRACE-CERTIFICATION-20260831-01
Baseline: e0a9d5a

The canonical runtime environment contains the Langfuse public and secret configuration (values not emitted), a configured base URL, and `LANGFUSE_TRACING_ENABLED=true`. The agent-platform environment has Langfuse 4.14.2 installed. `Langfuse.auth_check()` returned `True`.

A diagnostic observation was created and flushed. The SDK returned trace id `277c13173fe16c9195e7e524f1db1a29`; the subsequent API lookup returned `NotFoundError`, and a five-minute trace listing returned zero matching traces. Therefore authentication is proven, but remote export acceptance/visibility is not proven.

Result: `LANGFUSE_LIVE_EXPORT=FAIL` (unverified remote visibility). No old Nova or Agent Platform reasoning was invoked.
