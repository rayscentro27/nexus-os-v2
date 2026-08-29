# Nexus Oracle Resource Budget — 2026-08-29

Observed read-only: Oracle Linux 9.7 aarch64, 4 CPU, 22 GiB RAM, approximately
20 GiB available memory, swap unused, root filesystem 30 GiB with about 7.4
GiB free at inspection. Hermes, Ollama, and SearXNG were healthy.

| Resource | Budget / policy |
|---|---|
| CPU | shared constrained host; bounded workers and no assumed CPU controller |
| RAM | preserve headroom for Ollama and SearXNG; no unbounded concurrency |
| Disk | reserve space for existing services; no new large model/image without review |
| Network | loopback/private services; no public ingress |
| Runtime | rootless Podman and user-level Hermes supervision |

Placement: ORACLE_FREE_TIER for Hermes, Ollama, SearXNG, containers, and bounded
background intelligence. Resource-heavy or paid services require separate
authority.
