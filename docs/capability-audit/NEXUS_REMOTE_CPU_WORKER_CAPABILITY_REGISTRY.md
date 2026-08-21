# Worker Capability Registry

Enabled in this foundation:

- `evidence_ingestion.crawl4ai`

Contract-only/local-test path:

- `evidence_ingestion.markitdown` (remote filesystem execution remains denied)

Denied:

- generic shell, arbitrary Python, browser agent, computer use
- social publishing, email, Stripe, trading execution
- meeting bot, creative GPU, avatar, voice, unrestricted HTTP

Unknown capabilities and adapters fail closed. The registry is explicit and does not grant authority to the worker.
