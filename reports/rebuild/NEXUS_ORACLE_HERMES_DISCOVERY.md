# Oracle Hermes Discovery — 2026-08-28

`DISCOVERY=READ_ONLY`

The existing approved SSH path reached the existing Oracle VM. No VM was
created or resized, no billing configuration was changed, and no secret value
was read or printed.

| Field | Evidence-backed result |
|---|---|
| Oracle reachable | YES |
| Hostname class | Existing private Oracle Linux worker |
| OS | Oracle Linux 9.7 |
| Kernel | Linux 6.12.0-109.67.6.el9uek.aarch64 |
| Architecture | aarch64 / ARM64 |
| CPU | 4 |
| RAM | 22 GiB total; about 20 GiB available |
| Swap | 5 GiB; unused |
| Root disk | 30 GiB total; 11 GiB free |
| Uptime | 60 days, 14 hours at observation |
| Load / CPU | load 0.00; 98.4% idle in bounded sample |
| Capacity | PASS_WITH_LIMITS — adequate for non-local-LLM Hermes; disk is limiting |

Existing services were not restarted or reconfigured:

| Service | State | Listener / exposure |
|---|---|---|
| Ollama | installed/running; API OK; 2 models | `127.0.0.1:11434`; private |
| SearXNG | installed/running; HTTP 200 | `127.0.0.1:8888`; private |
| Docker | absent | none |
| Podman | absent | none |
| Python | `/usr/bin/python3` 3.9.25 | available |
| uv | absent | none |
| Git | 2.52.0 | available |
| curl | 7.76.1 | available |

There was no Hermes listener and no public Hermes endpoint. Existing Ollama
service memory usage was about 3.4 GiB in the metadata sample. Ollama and
SearXNG are `MUST_NOT_DISTURB=YES`.

`CPU_HEADROOM=PASS`; `RAM_HEADROOM=PASS`; `DISK_HEADROOM=PASS_WITH_LIMITS`;
`NETWORK_HEADROOM=PASS_FOR_PRIVATE_SSH`; `SERVICE_CONFLICT_RISK=LOW_IF_LOOPBACK_AND_ISOLATED`.
`ORACLE_HERMES_CAPACITY=PASS_WITH_LIMITS`.

The official NousResearch tag `v2026.8.27` was verified with `git ls-remote`.
The peeled source commit is
`5fc308a70719a83cccdbba4c0e39c23f5a8239d5` (annotated tag object
`fcebd62163497e77e5de00d26d2ed86cb4ef8761`). Official documentation identifies
the API server and supports Docker on x86_64 and aarch64. No exact official
image digest was confirmed, so an unverified image will not be used.
