# WP9E Oracle resource audit

Probe date: 2026-09-02. Existing authorized SSH path was used; no service was
restarted and no scheduler was touched.

| Field | Evidence |
|---|---|
| Host | `nexus-llm-worker` |
| OS/kernel | Oracle Linux Server 9.7; Linux 6.12.0-109.67.6.el9uek.aarch64 |
| Architecture/CPU | aarch64; 4 vCPU; Neoverse-N1 |
| Memory/swap | 22 GiB RAM; 5 GiB swap; 0 swap used |
| Disk | 30 GiB root; 7.5 GiB free (75% used) |
| Services | Ollama 0.21.2, SearXNG, Hermes in Podman container |
| Host tools | Podman and Git; Node/npm/host Chromium absent |
| Browser | Hermes container has Playwright-managed Chromium headless shell and FFmpeg |
| Health | HEALTHY at probe: load 0.02/0.02/0.00; Ollama loopback responded |

The Oracle host is suitable for bounded CPU/browser worker jobs, not GPU
generation or uncontrolled artifact growth. Free-tier billing/bandwidth
limits remain provider-account facts not queried by this probe.
