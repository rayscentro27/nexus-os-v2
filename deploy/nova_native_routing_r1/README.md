# NOVA_OBJECTIVE_INTAKE_AND_NATIVE_ROUTING_REPAIR_R1 — promoted 2026-11-16

## Nova (Oracle)
- New immutable release: `/home/opc/.nexus/releases/nova-operator-v1-20261116-native-routing-r1`.
  It is a copy of `nova-operator-v1-20261114-research-notify-repair-v1`, and only `scripts/nova/nova_telegram_worker.py` differs.
  The worker sha256 is `069188f134c470ce994bdab27c7ea7026090997001480862874d68c0b95e8793`. The change is in `nova_telegram_worker.native_routing_r1.patch`.
- Activated by drop-in `~/.config/systemd/user/nova-telegram-oracle.service.d/<243 z>-nr1.conf`, which sorts last.
- **Rollback:**
  1. `rm` that drop-in.
  2. `systemctl --user daemon-reload && systemctl --user restart nova-telegram-oracle.service`.
  3. Nova then returns to research-notify-repair-v1.

## Nexus MCP bridge (Mac)
- New immutable release: `~/.nexus/releases/nexus-capability-actions-20261116-project-context-v1`.
  It is a copy of `-20261108-ai-usage-ledger-v1`, plus `services/nexus_mcp/project_reader.py` and the `nexus_get_project` / `nexus_get_projects` registration (`mcp_server_project_tools.patch`).
- LaunchAgent `~/Library/LaunchAgents/com.nexus.nexus-mcp-bridge.plist` points at the new release. The backup is `com.nexus.nexus-mcp-bridge.plist.before-project-context-20261116`.
- **Rollback:**
  1. Copy the backup plist back over `com.nexus.nexus-mcp-bridge.plist`.
  2. `launchctl bootout gui/$(id -u) <plist>; launchctl bootstrap gui/$(id -u) <plist>`.

## Contract
`scripts/nova/tests/test_nova_native_routing_r1.py`. Set `NOVA_WORKER_UNDER_TEST` to a worker file, and `NOVA_WORKER_EXPECT` to FIXED or DEFECT.

## Update (02:23 UTC) — project tools exposed live
- **Bridge is now on `nexus-capability-actions-20261116-project-context-v3`.**
  - v1 adds `nexus_get_project` and `nexus_get_projects`.
  - v2 adds the SEP-2549 `ttlMs=300000` on tools/list.
  - v3 adds `nexus_get_project_approvals`.
  - v1 and v2 remain on disk.
- **Hermes:** the stale, never-expiring `nexus_mcp_remote` entry in `/opt/data/profiles/nova_nexus/cache/mcp_schema_cache.json` was removed.
  - Backup: `mcp_schema_cache.json.bak-native-routing-r1-20261116T013304Z`.
  - `nexus-hermes-0225.service` was restarted at 02:23:14 UTC. No config change.
  - The gateway re-discovered 120 nexus tools, including the 3 project tools.
- **Full rollback order:**
  1. Bridge: restore `com.nexus.nexus-mcp-bridge.plist.before-project-context-20261116`, then bootout + bootstrap.
  2. Nova: remove the `<243 z>-nr1.conf` drop-in, then daemon-reload and restart nova-telegram-oracle.
  3. Hermes: restart `nexus-hermes-0225.service` so it re-lists tools from the restored bridge. The cache backup is optional to restore.
