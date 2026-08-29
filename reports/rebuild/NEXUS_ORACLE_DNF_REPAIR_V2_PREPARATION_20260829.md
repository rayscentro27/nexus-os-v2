# Oracle DNF Repair V2 Preparation — 2026-08-29

`DNF_REPAIR_V2_PREPARATION=COMPLETE`
`PREVIOUS_REPAIR_GATE=HG-WP2-B-ORACLE-DNF-REPAIR-20260829-01`
`PREVIOUS_REPAIR_RESULT=ATTEMPTED_THEN_ROLLED_BACK_SUCCESSFULLY`

## Read-only Oracle inspection

The restored service is `nexus-searxng.service`, running as
`nexus-searxng:nexus-searxng` with:

```text
/opt/nexus-searxng/venv/bin/searxng-run
```

There are no existing service drop-ins and no pre-existing `LD_LIBRARY_PATH`.
The service currently maps the private SQLite library, while the global
linker cache selects it first. SearXNG and Ollama are healthy on their
existing loopback endpoints.

## Corrected drop-in

Path:

```text
/etc/systemd/system/nexus-searxng.service.d/sqlite-library.conf
```

Exact contents, byte-for-byte:

```ini
[Service]
Environment="LD_LIBRARY_PATH=/opt/nexus-searxng/sqlite/lib"
```

An isolated temporary fixture containing this exact assignment passed
`systemd-analyze verify` with return code 0 and no parser errors. The next
execution gate additionally requires `systemctl daemon-reload`, then an
effective-environment check before any SearXNG restart. If the check does not
contain exactly `LD_LIBRARY_PATH=/opt/nexus-searxng/sqlite/lib`, rollback must
occur immediately without restarting SearXNG.

## Pending gate

`NEW_DNF_REPAIR_GATE_ID=HG-WP2-B-ORACLE-DNF-REPAIR-20260829-02`
`NEW_GATE_STATUS=PENDING`

The gate authorizes only the corrected loader scoping, SearXNG-only restart,
health/isolation checks, and read-only DNF/Podman preview checks afterward. It
does not authorize Podman installation, Hermes deployment, package/database/
cache repair, repository changes, firewall or OCI changes, credential changes,
or any consequential Nexus action.

`ORACLE_MODIFIED_THIS_TASK=NO`
`PODMAN_INSTALLED=NO`
`HERMES_INSTALLED=NO`
