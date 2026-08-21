# Mac Mini and Remote CPU Placement Update

MarkItDown remains `MAC_MINI_ISOLATED_WORKER` and `GOOD`.

Crawl4AI remains `REMOTE_CPU_WORKER` as the preferred live placement. The current Mac cannot certify it because macOS 12.7.6 lacks a compatible Playwright Chromium runtime. The Mac therefore remains the Nexus control/private-state/lightweight-compute plane; browser crawling and batch CPU workloads belong in isolated Linux workers when a provider is safely configured.

No provider, scheduler, cloud account, or ongoing cost was created in this phase.
