# Oracle Hermes Deployment — 2026-08-28

`DEPLOYMENT_STATUS=STOPPED_DNF_TRANSACTION_PREVIEW_FAILURE`
`PODMAN_GATE_VERIFIED=YES`
`ORACLE_HOST_MODIFIED=NO`

Target: `HERMES_VERSION=0.20.6`, `TAG=v2026.8.27`, peeled commit
`5fc308a70719a83cccdbba4c0e39c23f5a8239d5`.

`WP2_B_DEPENDENCY_GRAPH_VALID=YES`
`WP2_A_HISTORICAL_STATUS=BLOCKED_HISTORICAL_ONLY; Intel Mac NO_GO preserved; Mac Hermes 0.14.0 preserved; architecture pivot recorded; gate reuse prohibited`
`WP2_B_ACTUAL_PREREQUISITES=WP0-A, WP1-A, WP1-B, WP1-D; all are proven/completed prerequisite packages and no longer depend on WP2-A`

Official platform support identifies a supported ARM64 container path, but
Oracle has neither Docker nor Podman installed. Hermes is **not installed**;
there is no process, config load, provider, session, memory, reasoning, or
restart proof yet.

`SELECTED_RUNTIME=PODMAN`
`ORACLE_RUNTIME_SUPPORTED=YES`
`HERMES_ON_PODMAN=REQUIRES_REAL_CERTIFICATION`
`CONTAINER_RUNTIME_INSTALL_REQUIRED=YES`
`TRANSACTION_PREVIEW=FAILED_DNF_SEGMENTATION_FAULT_EXIT_139`

The approved exact Podman gate was verified, but the privileged transaction
preview segfaulted twice before producing a transaction, first normally and
again with DNF plugins disabled. No installation command was executed after
the failure. A successful preview is required before package modification.

The predecessor `HG-WP2-B-ORACLE-CONTAINER-RUNTIME-20260828-01` is `HELD` and
must not be reused. Exact replacement gate:
`HG-WP2-B-ORACLE-PODMAN-INSTALL-20260828-02` (`PENDING`).

The new gate authorizes one host modification only: installation of the exact
Podman package and its DNF-resolved dependencies. It does not authorize Docker
Engine, a Docker daemon, cloud or firewall changes, OCI VCN/security changes,
provider credentials or paid usage, Hermes or bridge deployment, TruthKernel
mutation, Active Operator, routines, delegation, voice, live trading,
payments, or client-production mutation.

```text
EXACT_PACKAGES=podman-6:5.8.2-6.0.1.el9_8.aarch64 plus dnf-resolved dependencies
EXACT_INSTALL_SOURCE=ol9_appstream
EXACT_COMMANDS=dnf install --setopt=install_weak_deps=False podman-6:5.8.2-6.0.1.el9_8.aarch64 (not executed)
SERVICES_CREATED=none planned
FILES_CHANGED=package-manager metadata and host runtime files only; no Nexus source files
PORTS_CHANGED=none; Hermes must bind 127.0.0.1 only
FIREWALL_CHANGED=none
ROLLBACK=stop/disable runtime; remove only newly installed runtime packages if approved; preserve existing services
DISK_IMPACT=27.43 MiB download / 93.83 MiB bounded resolved installed-size estimate
MINIMUM_REQUIRED_FREE_SPACE_AFTER=approximately 10.47 GiB
WHY_REQUIRED=Oracle-native standalone Podman is required to run the official ARM64 Hermes image; no runtime exists
```

No sudo, package installation, system-service change, firewall change, VM
resize, provider credential change, paid activation, or public exposure was
performed. Rollback is ready by isolation design and touches neither Mac
Hermes nor TruthKernel.
