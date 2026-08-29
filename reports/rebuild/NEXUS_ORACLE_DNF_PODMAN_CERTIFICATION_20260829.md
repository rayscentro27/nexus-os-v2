# Oracle DNF Repair and Podman Certification — 2026-08-29

`DNF_REPAIR_V2_GATE_VERIFIED=YES`
`DNF_REPAIR_CERTIFIED=YES`
`PODMAN_GATE_STILL_EXACT=YES`
`PODMAN_INSTALL_ELIGIBLE=YES`
`PODMAN_INSTALLED=YES`
`PODMAN_VERSION=5.8.2`

The corrected SearXNG systemd drop-in was written byte-for-byte as:

```ini
[Service]
Environment="LD_LIBRARY_PATH=/opt/nexus-searxng/sqlite/lib"
```

The effective environment was verified before restart. Global `ldconfig`
resolution selected `/lib64/libsqlite3.so.0`; SearXNG restarted separately,
returned HTTP 200 on `127.0.0.1:8888`, and mapped its private SQLite library.
An ordinary process did not map that private library. Ollama remained healthy.

The exact approved Podman preview completed without an `LD_LIBRARY_PATH`
override: 14 packages, 20M download, 66M installed, no removals or upgrades.
The approved Podman transaction then installed successfully. Rootless Podman
is active for `opc` with existing subuid/subgid ranges. A disposable official
Podman hello image pulled, created, exited 0, and was removed. No Podman
socket, public port, firewall, or OCI ingress was added.

Hermes was not installed or started. The official ARM64 manifest for
`v2026.8.27` was reverified at:

```text
sha256:e3f4f0679f15556d5e09369cc36bf1074351b2d37bdd672dae593dfd07495180
```

The existing Oracle Ollama exposes `gemma3:4b` locally, but rootless bridge
networking could not reach its loopback listener. Official Hermes Linux
guidance supports host networking for host-local inference; this was therefore
included in the pending deployment design while keeping Hermes API binding at
host loopback only.

`HERMES_DEPLOYMENT_GATE_ID=HG-WP2-B-ORACLE-HERMES-DEPLOY-20260829-03`
`HERMES_DEPLOYMENT_GATE_STATUS=PENDING`
