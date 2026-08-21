# Retry, Health, and Usage

The initial worker is synchronous and bounded to one concurrent job. It exposes no autonomous retry loop and no scheduler. Invalid URL/policy/capability failures are non-retryable. A future provider adapter may retry only transient transport failures with an explicit job-idempotent policy.

Worker heartbeat is optional and includes worker ID, provider, capabilities, active/completed/failed counts, freshness, and authority state. Mission Control displays it separately from core health. Cost is reported as `COST_UNKNOWN` unless a provider supplies trustworthy usage metadata; costs are never fabricated.

Cancellation is currently `NOT_AVAILABLE` for the synchronous worker and must be implemented only with a provider contract that can safely terminate one bounded job.
