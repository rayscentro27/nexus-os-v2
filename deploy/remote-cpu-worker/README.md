# Nexus Remote CPU Worker

This is a fixed-command Linux container for the provider-neutral Nexus worker contract. It exposes only authenticated `/v1/jobs` capability submission and `/health`; it does not expose a shell or accept arbitrary commands.

The container currently permits `evidence_ingestion.crawl4ai`. MarkItDown remains local-file scoped and is not enabled for remote filesystem access. The image installs Chromium inside Linux so Crawl4AI can run in a browser-capable environment.

The image is not a scheduler and does not contain Nexus credentials. Production deployment still requires an authenticated network boundary, tenant-scoped artifact transport, bounded resource limits, and an explicit provider adapter.
