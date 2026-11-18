# NEXUS_AUTOMATIC_DIRECTIVE_AND_CONTINUATION_R1 — deployed 2026-11-16

## Source of truth (repo)
- `scripts/nexus_agent_platform/department_directive.py`. Its tests are in `tests/test_department_directive.py`.
- `scripts/nova/directive_notifications.py`. Its tests are in `scripts/nova/tests/test_directive_notifications.py`.

## Durable dispatcher (Mac)
- Release `~/.nexus/releases/nexus-capability-actions-20261116-directive-continuation-v2`. It is copied from `rea-harness-v4` and adds `department_directive.py`, the `DEPARTMENT_DIRECTIVE` route, and a worker handler.
- The plist adds the allowed sources `NOVA_MCP_DEPARTMENT_DIRECTIVE` and `NEXUS_DIRECTIVE_CONTINUATION`. The backup is `com.nexus.durable-dispatcher.plist.before-directive-continuation-20261116`.
- **Rollback:** restore the backup plist, then bootout + bootstrap.

## Nexus MCP bridge (Mac)
- Release `nexus-capability-actions-20261116-directive-v6`. Its lineage is project-context v1→v3, then directive v4→v6.
- New tools: `nexus_create_department_directive`, `nexus_get_department_directive`, `nexus_get_directive_events`.
- **Rollback:** point the plist back at `…project-context-v3`, or use the pre-session backup `.before-project-context-20261116`.

## Nova (Oracle)
- Release `nova-operator-v1-20261116-directive-notify-v1`. It is `native-routing-r1` plus `directive_notifications.py` and the notifier patch (`nova_notifier.patch`).
- `NOTIFY_SINCE=2026-11-16T06:01:46Z`.
- The drop-in is `<244 z>.conf`.
- **Rollback:** remove that drop-in, daemon-reload, restart Nova. Nova then returns to native-routing-r1.

## Hermes
- `nexus-hermes-0225.service` was restarted twice to re-list tools. No config change.
