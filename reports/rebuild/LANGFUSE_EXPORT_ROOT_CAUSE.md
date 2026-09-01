# Langfuse export root cause

The SDK is 4.14.2 and `auth_check()` succeeds. The adapter exports through Langfuse's OpenTelemetry observation API and flushes through `OtelAdapter.flush()` / SDK `flush()`.

A diagnostic span flushed without a client-side exception, but trace lookup and observation lookup returned no matching remote records. Export acceptance is therefore unverified. The most likely actionable class is exporter/remote-ingestion visibility rather than authentication; this report does not claim a narrower cause without server acknowledgement.

The current Hermes child previously lacked the Langfuse package. Installing the approved 4.14.2 package in that runtime was required for child-side exporter availability. No model call was added.
