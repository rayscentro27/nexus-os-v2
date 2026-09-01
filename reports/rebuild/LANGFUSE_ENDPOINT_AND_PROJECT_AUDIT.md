# Langfuse endpoint and project audit

The SDK-supported host variable is `LANGFUSE_BASE_URL`; the configured host is `cloud.langfuse.com`. Public and secret keys are configured in the canonical runtime environment. No separate OTel endpoint is configured, so the Langfuse SDK exporter is authoritative.

Authentication succeeded. Native and OTel diagnostic traces were each found through the configured Langfuse API after bounded ingestion delay, demonstrating that ingestion and query target the same deployment/project. Secret values are intentionally omitted.
