# Oracle Hermes Deployment Attempt — 2026-08-29

`DEPLOYMENT_GATE=HG-WP2-B-ORACLE-HERMES-DEPLOY-20260829-04`
`GATE_APPROVAL=APPROVED`
`IMAGE_PULL=COMPLETED`
`CONTAINER_CREATE=COMPLETED`
`CONTAINER_START=FAILED`
`ROLLBACK=COMPLETED`
`ORACLE_HERMES_INSTALLED=NO`
`ORACLE_HERMES_RUNNING=NO`

The pinned ARM64 image was pulled and the gate-authorized container was
created. Rootless Podman could not start it because the Oracle cgroup v2 user
hierarchy exposes `memory` and `pids` but not the `cpu` controller; the
gate-authorized `--cpus=2` limit therefore failed in `crun`. The failed,
non-running container was removed. The isolated Hermes data/config and local
API-key file remain protected on Oracle; the API key was not printed or
committed.

Ollama and SearXNG remained healthy. No Hermes listener, public endpoint,
bridge, Telegram action, or Active Operator action occurred.

The exact gate was not replayed. A replacement pending gate,
`HG-WP2-B-ORACLE-HERMES-DEPLOY-20260829-05`, omits only the unsupported CPU
limit while retaining the approved image, host-loopback API, isolated state,
provider, and minimum capability boundaries.
