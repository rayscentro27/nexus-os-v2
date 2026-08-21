# Worker Authentication and Tenant Security

HTTP submission requires a shared scoped secret, timestamp, HMAC integrity signature, a bounded request body, a unique job ID, and a five-minute clock window. Unknown schema, capability, adapter, source, or tenant context is rejected. Repeated job IDs are deduplicated for the worker lifetime.

The worker preserves tenant context and returns it in the result. It does not accept tenant context from the result or permit a remote job to change it. Remote MarkItDown filesystem access is intentionally disabled; Crawl4AI accepts only a public URL source.

The container has no Nexus secrets. Stripe, Telegram, brokerage credentials, arbitrary shell, and unrelated filesystem access remain unavailable.
