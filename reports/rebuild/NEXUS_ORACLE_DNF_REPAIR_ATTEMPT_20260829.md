# Oracle DNF Repair Attempt — 2026-08-29

`DNF_REPAIR_GATE=HG-WP2-B-ORACLE-DNF-REPAIR-20260829-01`
`DNF_REPAIR_GATE_VERIFIED=YES`
`HOST_MUTATION_ATTEMPTED=YES`
`ROLLBACK_EXECUTED=YES`
`ROLLBACK_RESULT=SUCCESS`
`FINAL_HOST_STATE_RESTORED=YES`
`PERSISTENT_NET_CHANGE=NO`
`ORACLE_HOST_MODIFIED=NO (final state; a mutation was attempted and rolled back)`
`PODMAN_INSTALLED=NO`
`HERMES_INSTALLED=NO`

## Result

The approved repair was attempted once. The loader configuration was backed
up, the global loader entry was temporarily removed, and `ldconfig` selected
system SQLite. A SearXNG systemd drop-in was then created, but the generated
file contained invalid escaping. `systemd` ignored the environment assignment;
SearXNG consequently used system SQLite 3.34.1 and logged that the version was
below its required minimum.

The gate's rollback condition was met. Rollback restored the global loader
configuration, removed the invalid drop-in, ran `ldconfig`, reloaded systemd,
and restarted only `nexus-searxng.service`. After the restart, SearXNG returned
HTTP 200 on `127.0.0.1:8888` and again mapped the private SQLite library.
Ollama remained healthy on its existing loopback endpoint.

## Sanitized evidence

| Check | Result |
|---|---|
| Gate status / exact action / identity / expiry / replay | PASS / PASS / PASS / PASS / PASS |
| Backup | Created under protected Oracle-local path; readable; not committed |
| Global SQLite after rollback | Private SearXNG SQLite selected again, as before repair |
| SearXNG after rollback | Active; HTTP 200; `127.0.0.1:8888` |
| Private SQLite after rollback | Mapped by SearXNG process |
| Ollama | HTTP 200; not restarted |
| DNF certification | NOT RUN after rollback |
| Podman installation | NOT RUN |
| Hermes deployment | NOT RUN |

No DNF, RPM database, cache, package, firewall, OCI, Ollama, or Hermes changes
were made. No public endpoint was created. The host is left in its prior
working state, but the DNF repair is not certified and the Podman gate is not
eligible for execution.

`NEXT_ACTION=obtain a new exact authorization for a corrected repair execution`

The corrected pending gate is
`HG-WP2-B-ORACLE-DNF-REPAIR-20260829-02`. No Oracle changes were made while
preparing that gate.
