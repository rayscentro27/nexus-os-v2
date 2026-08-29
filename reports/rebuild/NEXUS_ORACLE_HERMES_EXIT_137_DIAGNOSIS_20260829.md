# Oracle Hermes Exit-137 Forensics — 2026-08-29

## Scope and disposition

This is a read-only forensic record for deployment gate
`HG-WP2-B-ORACLE-HERMES-DEPLOY-20260829-05`. No Oracle mutation, container
creation, or Hermes restart was performed during this diagnosis.

The exit was not a host-memory OOM. The preserved Podman event and systemd
journal sequence proves that the Oracle user manager began session shutdown,
stopped the rootless Podman scope, waited for the stop timeout, and then sent
SIGKILL. Podman recorded the resulting container exit as 137. The gateway had
already opened its API on loopback before that external shutdown.

## Reconstructed timeline (UTC)

| Event | Evidence timestamp |
|---|---|
| Gate approved | `2026-08-29T03:16:00.792026+00:00` (TruthKernel) |
| Deployment command start | `NOT_PRESERVED` |
| Podman create | `2026-08-29T03:24:04.894302+00:00` (system journal) |
| Podman init | `2026-08-29T03:24:04.970239+00:00` |
| Podman start | `2026-08-29T03:24:04.974636+00:00` |
| s6/container initialization | `2026-08-29T03:24:04+00:00` (journal precision) |
| Hermes setup and bundled-skill synchronization | `2026-08-29T03:24:05+00:00` (journal precision) |
| First gateway API ready | `2026-08-29T03:24:12.100+00:00` (Hermes log) |
| User manager/session shutdown begins | `2026-08-29T03:24:25+00:00` (systemd journal) |
| Gateway receives SIGTERM | `2026-08-29T03:24:25.608+00:00` (Hermes log) |
| Scope stop times out and systemd sends SIGKILL | `2026-08-29T03:24:35+00:00` (systemd journal) |
| Podman records `died`, exit 137, then `restart` | `2026-08-29T03:24:35.916790835+00:00` / `03:24:35.925897625+00:00` |
| Rollback container removal | `2026-08-29T03:25:08.977785191+00:00` (system journal) |

The exact deployment runner start, rollback-start, and container-removal
command invocation timestamps were not preserved as separate receipts. The
first API-ready event occurred 7.125 seconds after the precise Podman start
event; the final exit event occurred 30.942 seconds after it. The gateway's
first SIGTERM occurred 13.508 seconds after Podman start. These are observed
intervals, not inferred process-start times.

## Recovered command and controls

The exact sanitized command recorded in the gate and deployment report was:

```text
podman run -d --name nexus-hermes-0206 --restart unless-stopped --network host --memory=4g -v /home/opc/.local/share/nexus-hermes-0206:/opt/data:Z --env-file /home/opc/.config/nexus-hermes-0206/api.env -e API_SERVER_ENABLED=true -e API_SERVER_HOST=127.0.0.1 -e API_SERVER_PORT=8642 -e API_SERVER_CORS_ORIGINS= -e HERMES_UID=1000 -e HERMES_GID=1000 -e HERMES_DOCKER_BINARY=podman docker.io/nousresearch/hermes-agent@sha256:e3f4f0679f15556d5e09369cc36bf1074351b2d37bdd672dae593dfd07495180 gateway run
```

`DETACHED_MODE=YES`; `MEMORY_LIMIT=4g`; `MEMORY_SWAP_LIMIT=UNSET`;
`PIDS_LIMIT=UNSET`; `CPU_LIMIT=UNSET`; `SHM_SIZE=UNSET`;
`RESTART_POLICY=unless-stopped`; `STOP_TIMEOUT=DEFAULT/UNSET`;
`INIT=IMAGE/S6`; `SYSTEMD_MODE=NO`; `HEALTHCHECK=UNSET`;
`ENV_FILE=AUTHORIZED_PATH_ONLY`; `VOLUME_MOUNTS=AUTHORIZED /opt/data ONLY`.
The image entrypoint is the pinned image dispatcher and the command is
`gateway run`.

No repository runner containing a timeout, kill, cleanup trap, or `podman
stop/kill` for this deployment was found. The preserved system journal does
show systemd user-session cleanup as the actor that stopped the Podman scope.

## Podman, systemd, and cgroup evidence

Observed event sequence: `refresh, create, pull, init, start, died(exit=137),
restart, remove`. Podman reported no OOM event; the removed container's prior
inspect evidence recorded `OOMKilled=false`.

At failure time systemd recorded:

- `Stopping User Manager for UID 1000`
- `Activating special unit Exit the Session`
- stopping the Podman/conmon/crun scopes
- `libpod scope: Stopping timed out. Killing.`
- SIGKILL sent to s6 and Hermes processes
- `Failed with result 'timeout'`
- user manager deactivated, followed by a new user manager session

The container-specific cgroup no longer exists after rollback. The surviving
rootless user cgroup has `memory.max=max`, `memory.high=max`, `pids.max=max`,
and zero `memory.events`/`memory.events.local` OOM or kill counters. The gate's
`--memory=4g` was therefore not proven to have been exceeded. No host kernel
OOM, swap pressure, filesystem, or hardware fault was found.

## Hermes startup evidence

The official tagged image path is consistent with the observed sequence:
s6-overlay `/init`/`s6-svscan` as PID 1, stage-2 setup and profile
reconciliation, supervised gateway service, then gateway API startup. The
image's setup completed successfully, 82 bundled skills were synchronized,
the gateway control socket and API became ready on loopback, and no Python
exception or Hermes gateway self-termination was recorded before the external
SIGTERM.

The preserved state contains initialized config, sessions/databases, logs,
gateway state, and bundled skills. It is internally readable but is partial
startup state rather than certified runtime state. Reuse is **not proven safe**
for a future deployment; a fresh isolated state is recommended unless a later
approved preflight explicitly validates and migrates it.

## Hypothesis classification

| Hypothesis | Status | Evidence | Counterevidence |
|---|---|---|---|
| A — container cgroup OOM | CONTRADICTED | 4g was configured, but exit state and surviving cgroup show no OOM evidence | `OOMKilled=false`; zero OOM counters; no container cgroup after rollback |
| B — host OOM | CONTRADICTED | host remained healthy | no kernel OOM, no memory pressure, ample available memory |
| C — external timeout or cleanup SIGKILL | SUPPORTED / PROVEN CLEANUP PATH | systemd user manager/session shutdown stopped the Podman scope; stop timeout sent SIGKILL; exit became 137 | no runner timeout was found; timeout itself is not proven |
| D — Podman/crun runtime kill | POSSIBLE as mechanism, not root cause | systemd stopped crun/conmon scopes during session cleanup | no independent crun fault or runtime bug evidence |
| E — Hermes s6 supervisor kill | CONTRADICTED as root cause | s6 supervised the gateway and gateway received SIGTERM from outside | s6 did restart the gateway after SIGTERM, but did not originate the user-manager shutdown |
| F — manual/operator kill | NOT_PROVEN | no operator kill receipt | systemd cleanup has a complete observed causal path |
| G — other | NOT_PROVEN | no additional proven cause | observed systemd cleanup sufficiently explains exit 137 |

## Resource-limit review

`MEMORY_LIMIT_COMPATIBLE=YES_NOT_PROVEN_CAUSAL`: 4 GiB is within the official
image's documented general runtime range and no memory event proves a breach.
`PIDS_LIMIT_COMPATIBLE=YES_NOT_APPLIED`: no explicit pids limit was configured.
`SHM_LIMIT_COMPATIBLE=YES_FOR_MINIMUM_PROFILE`: no browser/MCP capability was
enabled and no shared-memory failure was observed.

## Root-cause decision

`EXIT_137_ROOT_CAUSE=PROVEN_EXTERNAL_TIMEOUT_SIGKILL` is used here in the
canonical hypothesis vocabulary to mean **external user-session cleanup SIGKILL**;
an outer command timeout was not proven. Confidence is `HIGH` for the immediate
kill path.

Minimum corrective change: execute the rootless deployment under a persistent
Oracle user manager so SSH session logout cannot tear down the Podman scope.
The precise host-side prerequisite is `loginctl enable-linger opc` (or an
equivalent already-proven persistent user-manager mechanism). This is a host
mutation and is not executed by this diagnosis. A replacement deployment gate
was prepared separately and changes only that lifecycle prerequisite; all
Hermes image, network, data, provider, and capability boundaries remain fixed.

## Truth disposition

`HERMES_IMAGE_PRESENT=YES` remains true. Bundled-skill/state initialization is
not a successful Hermes installation. `ORACLE_HERMES_INSTALLED=NO` and
`ORACLE_HERMES_RUNNING=NO` remain true. No bridge or Telegram test was run.
