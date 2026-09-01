# Langfuse MCP provenance

MCP receipts retain tool, request, trace/update correlation, currentness,
source, item counts, filtered counts, status, and deduplication state. Hermes
events record selected tool names and a bounded deterministic result fingerprint.
Raw business/client payloads are not sent to Langfuse.
