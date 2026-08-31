# Nova Telegram Send Retry and Idempotency

Before: one immediate send plus one fixed one-second retry, errors collapsed to `None`, and no durable pending response.

After: bounded three-attempt policy by default, exponential backoff with jitter, `Retry-After` support for HTTP 429, eligible 5xx/408 responses, and transient network/timeout/reset classification. Permanent 4xx responses do not retry indefinitely.

Delivery records contain update id, Hermes run id, response hash, attempt count, last error/time, and Telegram message ids. A delivered record is never sent again. Failure-injection coverage confirms two transient failures, later success, unchanged response hash, no reasoning/tool rerun, and no duplicate send. Permanent failure records `FAILED_TERMINAL`.
