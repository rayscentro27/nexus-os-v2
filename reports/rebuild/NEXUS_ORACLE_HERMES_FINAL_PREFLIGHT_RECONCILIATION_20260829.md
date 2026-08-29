# Oracle Hermes Final Preflight Reconciliation — 2026-08-29

`HERMES_FINAL_PREFLIGHT_RECONCILIATION=COMPLETE`
`CURRENT_ORACLE_HOST_MODIFIED=YES`
`PERSISTENT_PUBLIC_NETWORK_CHANGE=NO`

## Current host truth

The successful loader repair and Podman installation are persistent Oracle host
changes. The earlier malformed repair was also a real mutation attempt and was
rolled back successfully. These facts are recorded separately:

```text
PREVIOUS_DNF_REPAIR_ATTEMPTED=YES
PREVIOUS_DNF_REPAIR_ROLLBACK_EXECUTED=YES
PREVIOUS_DNF_REPAIR_ROLLBACK_SUCCESS=YES
CURRENT_DNF_REPAIR_CERTIFIED=YES
CURRENT_SEARXNG_LOADER_ISOLATION_PERSISTENT=YES
CURRENT_PODMAN_INSTALLED=YES
CURRENT_PODMAN_VERSION=5.8.2
CURRENT_ORACLE_HOST_MODIFIED=YES
PERSISTENT_PUBLIC_NETWORK_CHANGE=NO
```

Oracle remains Oracle Linux 9.7/aarch64. Global SQLite resolves to the system
library, SearXNG maps its private library through its service-local drop-in,
and both SearXNG and Ollama are healthy. Podman is rootless-ready, with no
public Podman socket, firewall change, or OCI ingress change. Hermes is absent.

## Hermes gate reconciliation

Gate `HG-WP2-B-ORACLE-HERMES-DEPLOY-20260829-03` was held through the supported
TruthKernel hold operation. It was not approved, executed, or consumed. Its
contract did not explicitly bind the minimum capability profile or the
unattended tool-loop hard stop.

Replacement gate:

```text
HG-WP2-B-ORACLE-HERMES-DEPLOY-20260829-04
STATUS=PENDING
```

The replacement keeps Hermes API access at `127.0.0.1:8642` with no port
publish because host networking is used. Host networking is explicitly
justified by the failed rootless `slirp4netns`, `pasta`,
`host.containers.internal`, and host-gateway tests against Ollama’s host
loopback listener. It is a broader host-local reachability boundary than a
single-service proxy, so the initial capability profile is minimized:

```text
ROUTINES=OFF
DELEGATION=OFF
VOICE=OFF
DASHBOARD=OFF
MCP=OFF
BROWSER=OFF
UNRESTRICTED_SHELL=OFF
AUTONOMOUS_SKILLS=OFF
TOOL_LOOP_HARD_STOP=ON; exact_failure=5; idempotent_no_progress=5
```

The pinned official image remains the ARM64 digest
`sha256:e3f4f0679f15556d5e09369cc36bf1074351b2d37bdd672dae593dfd07495180`.
State is isolated at `/home/opc/.local/share/nexus-hermes-0206` mounted at
`/opt/data`. The local API key is generated only at deployment, stored in the
protected `api.env` file, and never printed or committed.

No Hermes deployment, bridge activation, Telegram E2E, or consequential action
was performed.
