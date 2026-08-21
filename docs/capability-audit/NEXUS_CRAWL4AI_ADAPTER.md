# Crawl4AI Contained Adapter

Crawl4AI is wrapped as a single-URL, shallow public-web evidence adapter. It accepts only HTTP/HTTPS URLs without credentials, cookies, forms, uploads, POST actions, authenticated sessions, or mutation workflows. URL resolution rejects localhost, loopback, link-local, private/reserved/multicast/metadata destinations, and revalidates the final redirect destination.

The pilot applies one page, bounded timeout, bounded output, no retries, robots checking, an identifiable Nexus user-agent, and no deep crawl. Failure to access a source is recorded as a bounded status such as `ROBOTS_BLOCKED`, `SOURCE_UNAVAILABLE`, `TIMEOUT`, or `DEPENDENCY_UNAVAILABLE`; circumvention is not attempted.

Certification result on this Mac: the adapter contract and safety tests pass, but a live Crawl4AI browser execution is not certified because macOS 12.7.6 cannot install/launch the required Playwright Chromium headless executable. This is an environment dependency blocker for the contained pilot, not a reason to weaken network restrictions.
