# Nexus Runtime Path Separation — R1

## Current state

The canonical checkout still contains active or service-adjacent mutable state:

| Path | Evidence / role | Current treatment |
|---|---|---|
| `data/runtime/` | Live operator, department, research-refresh and worker state files are present and change during operation. | Keep in place. Repository policy blocks committing it. |
| `reports/runtime/` | LaunchAgent and runtime jobs write heartbeats, monitor outputs and credential-catalog reports here. | Keep in place. Repository policy blocks committing it. |
| `reports/research/two_hour/` | Scheduled Research reports use the repository path. | Keep reports intact; review the writer before relocation. |
| `data/research*`, `artifacts/research/` | Research Rooms, findings, evidence and operational records may be locally unique. | Preserve; no automatic ignore, move, or deletion. |
| `~/.nexus/state/` | Existing Research MCP token/state and tunnel transport state are already outside the checkout. | Continue using established external runtime paths. |

## Safe separation decision

No active state was moved. LaunchAgents and workers use absolute paths into the current checkout, and no migration/rollback certification exists for changing those paths. Moving them now could break active Research, MCP or reporting services and risks losing the only local copy.

The machine-enforced pre-commit policy classifies runtime databases, queues, logs, caches, generated artifacts, and Research data separately and rejects them from routine commits. Existing exact-path ignore rules protect only previously verified generated/runtime outputs; Research knowledge remains visible and preserved.

## Future migration gate

Move an individual state family only after identifying its writer, readers, locking/atomic-write behavior, recovery copy, and an explicit external target. Update one service at a time, validate read/write behavior against a copied state, then switch the service with a documented rollback. Do not bulk-move `data/`, `reports/`, or Research collections.
