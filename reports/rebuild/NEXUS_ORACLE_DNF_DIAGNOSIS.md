# Oracle DNF Diagnosis — 2026-08-29

`WP2_B_DNF_DIAGNOSIS=COMPLETE`
`ORACLE_HOST_MODIFIED=NO`
`PODMAN_INSTALLED=NO`
`HERMES_INSTALLED=NO`

## Failure reproduction

The exact approved Podman preview was run only as a dry run. Both default and
`--noplugins` variants exited with `139` / `SIGSEGV` under root. `dnf
--version`, both repository listings, and both repository-disabled installed
package queries passed. A repository-disabled install preview reported no
enabled repositories and did not crash.

With identical repositories, target, and weak dependencies disabled, forcing
the system library path completed dependency resolution and returned the normal
dry-run abort:

```text
LD_LIBRARY_PATH=/lib64:/usr/lib64
Transaction Summary: Install 14 Packages
Total download size: 20 M
Installed size: 66 M
Operation aborted (dry run)
```

## Crash evidence

`CORE_DUMP_PRESENT=YES`. Both coredumps are `/usr/bin/python3.9` running DNF,
signal 11. The common useful path is:

```text
strlen -> vfprintf -> rpmlog (librpmio.so.9)
-> /opt/nexus-searxng/sqlite/lib/libsqlite3.so.0.8.6
-> SQLite3::exec (libdnf.so.2 + 0x9946c)
```

`/etc/ld.so.conf.d/nexus-searxng-sqlite.conf` globally adds
`/opt/nexus-searxng/sqlite/lib`; `ldconfig -p` selects that library ahead of
system SQLite. The running SearXNG process maps the private library. The
system-library override makes the identical DNF preview succeed. This proves a
global dynamic-loader conflict affecting libdnf’s SQLite path; it does not
prove RPM database corruption.

## Health and alignment

| Check | Result |
|---|---|
| RPM DB read | PASS; 795 packages |
| RPM DB verification | PASS; no relevant output |
| DNF history SQLite | PASS; `integrity_check=ok`, 13 transactions |
| Relevant package-file integrity | PASS |
| DNF stack alignment | `CONSISTENT_OL9_7_STACK`; EL9 rolling candidates present, no package ABI mismatch proven |
| Repository configuration | Normal Oracle Linux 9.7; six enabled OL9 repos |
| Python dnf/hawkey/libdnf/rpm/librepo imports | PASS individually |
| Memory/OOM/filesystem/kernel hardware | No pressure or errors observed |
| Persistent DNF cache | Approximately 892 MiB; no obvious corruption proven |
| Temporary-cache diagnostic | INCONCLUSIVE/ABORTED after timeout; temporary files removed; persistent cache untouched |

`ROOT_CAUSE_CLASS=D_PACKAGE_MANAGER_LIBRARY_OR_ABI_MISMATCH`
`ROOT_CAUSE_CONFIDENCE=HIGH`
`ROOT_CAUSE_EVIDENCE=default loader crashes in private SearXNG SQLite; explicit system SQLite override completes identical preview; coredump lands in libdnf SQLite execution; RPM/history/import/integrity checks pass.`

## Repair gate

`NEW_DNF_REPAIR_GATE_REQUIRED=YES`
`NEW_DNF_REPAIR_GATE_ID=HG-WP2-B-ORACLE-DNF-REPAIR-20260829-01`
`HOST_MUTATION_REQUIRED=YES`
`GATE_STATUS=PENDING`

The exact pending gate scopes removal of the private SQLite path from the
global loader configuration, adds a SearXNG-only systemd `LD_LIBRARY_PATH`,
runs `ldconfig`, reloads systemd, and restarts only SearXNG. It does not
install Podman, change repositories, touch databases/caches, or deploy Hermes.

## Alternative installer

`OFFICIAL_LINUX_INSTALL_ALTERNATIVE=YES_SAFE_INDEPENDENT` for future separate
evaluation. The tagged official `scripts/install.sh` uses managed `uv` and
Python 3.11 and can avoid DNF for the core install when curl and git are
available. It was audited only, not run, and does not change the container
deployment decision.
