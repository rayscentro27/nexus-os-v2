# Remote CPU Worker Prerequisites

Phase H intentionally does not provision AWS, GCP, Azure, RunPod, Modal, Coolify, or other infrastructure.

Before a remote CPU pilot, Nexus needs: a provider-neutral authenticated job transport; container/environment reproducibility; tenant-scoped input/output references; public-web egress policy; SSRF enforcement at both adapter and network boundary; bounded concurrency, timeout, retry and cancellation; receipt correlation; cost/usage metadata; worker heartbeat; and isolation so a failed browser/crawler cannot affect certified Nexus services.

The first remote pilot should use the existing evidence request/result contract and prove one bounded public URL job, with no new scheduler or authority layer.
