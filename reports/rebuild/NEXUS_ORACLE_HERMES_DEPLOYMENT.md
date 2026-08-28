# Oracle Hermes Deployment — 2026-08-28

`DEPLOYMENT_STATUS=STOPPED_AT_PREREQUISITE_GATE`

Target: `HERMES_VERSION=0.20.6`, `TAG=v2026.8.27`, peeled commit
`5fc308a70719a83cccdbba4c0e39c23f5a8239d5`.

Official platform support identifies a supported ARM64 container path, but
Oracle has neither Docker nor Podman installed. Hermes is **not installed**;
there is no process, config load, provider, session, memory, reasoning, or
restart proof yet.

`CONTAINER_RUNTIME_INSTALL_REQUIRED=YES`

Exact gate: `HG-WP2-B-ORACLE-CONTAINER-RUNTIME-20260828-01`

```text
EXACT_PACKAGES=podman (or Docker Engine; final choice requires Ray approval)
EXACT_INSTALL_SOURCE=Oracle Linux 9.7 supported package repository; capture exact versions before execution
EXACT_COMMANDS=dnf install; systemctl enable --now container runtime; version/health verification (not executed)
SERVICES_CREATED=container runtime system service if package path requires it
FILES_CHANGED=package-manager metadata and host runtime files only; no Nexus source files
PORTS_CHANGED=none; Hermes must bind 127.0.0.1 only
FIREWALL_CHANGED=none
ROLLBACK=stop/disable runtime; remove only newly installed runtime packages if approved; preserve existing services
DISK_IMPACT=measure package/runtime overhead before approval; 11 GiB free is the limit
WHY_REQUIRED=official pinned Hermes container deployment is the safest ARM64 path, but no runtime exists
```

No sudo, package installation, system-service change, firewall change, VM
resize, provider credential change, paid activation, or public exposure was
performed. Rollback is ready by isolation design and touches neither Mac
Hermes nor TruthKernel.
