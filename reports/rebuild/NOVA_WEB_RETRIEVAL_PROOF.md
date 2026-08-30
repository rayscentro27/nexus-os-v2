# Nova Web Retrieval Proof

The shared read-only capability now separates discovery from retrieval.
Development retrieval of `https://www.microsoft.com` returned HTTP 200 and
bounded readable HTML content. Tesla and Reuters rejected the current request
(403/401), which is recorded as a source-specific failure rather than a global
web refusal. Provenance records capability, URL, source type, freshness, and
read-only scope.
