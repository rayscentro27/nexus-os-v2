# Nova Stale Session and Memory Audit

## Active Ray conversation memory

Nova’s code resolves its memory directory to:

`/Users/raymonddavis/nexus-os-v2/scripts/data/runtime/nova_memory`

The active file for the audited Ray chat is `nova_1288928049.json`.

| Field | Observed value |
|---|---|
| Updated | `2026-08-30T22:45:49.913114Z` |
| Persisted turns | 20 |
| Current context build | 20 prior turns + current message = 42 messages |
| Negative capability assistant claims | 8 |
| Stale session beliefs | YES |

The persisted turns include assistant claims that Nova cannot send email, schedule appointments, access Gmail/Calendar, access external systems, use Google APIs, or directly check Nexus. These claims are not merely historical files on disk: the current context builder included the turns in the model message list.

## Broader memory inventory

There are 79 `nova_*.json` files in the Nova memory directory; a scan found two files containing the searched negative-capability patterns. No files were deleted or modified.

## Adjacent caches

The repository also contains older Telegram/Hermes context files such as `data/runtime/telegram_conversation_context.json`, `data/runtime/telegram_active_context.json`, and `data/runtime/agent_context/*`. They contain stale or legacy operational context. The current Nova worker’s direct memory path is the `scripts/data/runtime/nova_memory` directory; injection of the adjacent files into this live Nova prompt was not proven.

## Classification

| Data | Classification | Current-truth use |
|---|---|---|
| Prior assistant capability refusals | STALE | Must not be treated as capability truth |
| Prior conversation referents/decisions | Potentially useful historical context | Valid only as conversation context, not operational authority |
| Adjacent legacy Telegram contexts | LEGACY/STALE | Historical only unless explicitly revalidated |
| Current capability status | Not present as a proven persisted result | Must be queried/recorded on the live path |

No cleanup occurred during this audit.
