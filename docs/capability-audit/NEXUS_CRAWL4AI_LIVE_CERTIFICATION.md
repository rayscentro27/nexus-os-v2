# Crawl4AI Live Certification Status

Phase H proved the adapter contract and safety controls but could not launch Playwright Chromium on macOS 12.7.6. Phase I adds the Linux container entrypoint and remote provider contract needed to close that blocker.

Phase I-C closed the blocker through the Modal CPU worker. A bounded
`https://example.com/` job completed through the complete Nexus path:

`RemoteWorkerProvider -> Modal -> authenticated worker -> Crawl4AI/Chromium ->
nexus.remote-result.v1 -> Nexus validation -> nexus.evidence.v1 -> receipt ->
intake handoff -> Mission Control`.

The live result included source/material hashes and provenance. A second
transported acquisition produced the same material hash and was persisted by
Nexus as `DUPLICATE`. Live prohibited destinations (localhost, loopback,
RFC1918, link-local/metadata, and `file://`) were rejected without content.

The optional worker reports HEALTHY while idle with zero Modal tasks; core
runtime health remains independent of this capability.
