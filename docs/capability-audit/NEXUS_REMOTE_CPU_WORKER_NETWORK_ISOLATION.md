# Worker Network and Failure Isolation

The Crawl4AI adapter retains Phase H URL validation, DNS/private-address blocking, redirect validation, public-only policy, one-page depth, timeout, output-size, and no-mutation restrictions. A Linux deployment must add egress policy defense in depth before live use.

Browser, crawler, document, and future batch workloads belong in an isolated worker/container and never in Continuous Loop, Active Operator, Recovery Check, Hermes polling, or Mission Control processes. Worker outage must produce an optional degraded state and a bounded job error, not a restart storm or shell fallback.
