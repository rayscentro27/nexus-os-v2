# NEXUS OS — Final Overnight Completion R1: deployment record and rollback

Date: 2026-11-16 (UTC). Every release is immutable: a new directory was copied from the prior live release, and only the files listed below changed.

## Live components

### Admin Center (Netlify production, goclearonline.cc)
- **Commits:** main `70c86b60` (`38d46fcb` feat and `70c86b60` fix), fast-forwarded from `f99aa457`.
- **`admin-app/`:** the approved Admin Center package. Design unchanged. Built into `dist/admin` and served at `/admin/`.
- **Main-app routes:** `/admin/login`, `/admin/operations` and `/admin/review` are still served by the main app, because no file shadows them.
- **`netlify/functions/admin-nexus-state.mjs`:**
  - Guarded by `requireAdmin`.
  - Uses the privileged key `SUPABASE_SECRET_KEY || SUPABASE_SERVICE_ROLE_KEY`, the same pattern as `_tiktok.mjs`.
  - Reads `nexus_admin_read_model` and signs creative previews for 1 hour.
- **Rollback:** in Netlify, "Publish deploy" the previous production deploy (`f99aa457`), or `git revert 70c86b60 38d46fcb` on main and push.

### Admin read model (Supabase + Mac publisher)
- **Migration `20261116130000_nexus_admin_read_model.sql`:** additive. RLS is on, and anon/authenticated access is revoked (verified: an anon read returns 401).
- **Publisher:** `scripts/admin_read_model/publish_admin_read_model.py`, run by LaunchAgent `com.nexus.admin-read-model` every 300 s with nice 10.
  - Reads are bounded: 30 directives, 20 REA jobs, 15 research jobs, and 12 creative previews uploaded once, keyed by content hash.
- **Rollback:**
  - `launchctl bootout gui/$UID/com.nexus.admin-read-model`
  - The table can stay; it is inert.

### Nexus MCP bridge (Mac)
- **Release:** `nexus-capability-actions-20261116-overnight-bridge-v7` (from `...-directive-v6`).
- **Change:** `nexus_create_department_directive` accepts target `REA` and `business_id`; the directive reads expose `business_id` and `started_at`. Patch: `bridge_v7_server.patch`.
- **Certified:** MCP initialize OK, `tools/list` = 123 tools, `ttlMs=300000`, REA in the target enum, and `nexus_get_project(proj_98ef515bccee4b58)` returns OK.
- **Rollback:**
  - `cp ~/Library/LaunchAgents/com.nexus.nexus-mcp-bridge.plist.before-overnight-v7-20261116 ~/Library/LaunchAgents/com.nexus.nexus-mcp-bridge.plist`
  - Then bootout and bootstrap the agent.

### Durable dispatcher (Mac)
- **Release:** `nexus-capability-actions-20261116-overnight-dispatch-v3` (from `...-directive-continuation-v2`).
- **`department_directive.py`:**
  - Contract adds `business_id`/`venture_id`, `started_at` and `event_id`.
  - New REA target.
  - New events: `CAMPAIGN_CREATED`, `CREATIVE_CREATED`, `REA_WORK_STARTED`, `REA_WORK_COMPLETED` and `REA_WORK_FAILED`.
  - New function `continue_directives()`.
- **`continuation_engine.sweep()`:** calls `continue_directives()` on every continuation sweep. Patch: `dispatch_v3_continuation_engine.patch`.
- **Tests:** 20 directive/notification contract tests pass. Release suite: 63 pass; 1 fails, `test_rea_harness_r1::test_worker_projection_preserves_rea_linkage`. That failure is **pre-existing**: it fails identically on the prior live v2.
- **Rollback:** restore `~/Library/LaunchAgents/com.nexus.durable-dispatcher.plist.before-overnight-v3-20261116`, then bootout and bootstrap the agent.

### Nova (Oracle)
- **Release:** `nova-operator-v1-20261116-overnight-notify-v2` (from `...-directive-notify-v1`). Only `scripts/nova/directive_notifications.py` changed, sha256 prefix `51b9a897e9d8d61d`, with `NOTIFY_SINCE` kept unchanged.
- **Change:**
  - New kinds: `CREATIVE_CREATED`, `CAMPAIGN_CREATED`, `COMMERCE_OFFER_CREATED`, `REA_WORK_STARTED`, `REA_WORK_COMPLETED` and `REA_WORK_FAILED`.
  - Each message carries `EVENT_ID`, `BUSINESS_ID` and the related IDs.
  - Deduplication is keyed on `EVENT_ID`.
- **Activation:** a drop-in of 245 z's + `.conf` (sorts last).
- **Rollback:**
  - Remove that drop-in: `rm "$HOME/.config/systemd/user/nova-telegram-oracle.service.d/$(printf 'z%.0s' $(seq 1 245)).conf"`
  - Then `systemctl --user daemon-reload && systemctl --user restart nova-telegram-oracle.service`. This returns to `directive-notify-v1`.

## Deterministic directive continuation (`continue_directives`)
| Directive state | Action |
|---|---|
| RUNNING with a finished REA child | `REA_WORK_COMPLETED` and COMPLETE, or `REA_WORK_FAILED` + `PROJECT_BLOCKED` |
| FAILED with retries exhausted | `PROJECT_BLOCKED`, notified once |
| WAITING_APPROVAL, undecided | held (no action) |
| WAITING_APPROVAL + APPROVED | `PROJECT_CONTINUED` (resume) |
| Recoverable failure | bounded retry by the durable job (`max_attempts`), then the row above |

The n8n W1 policy's `governed_job_types` is unchanged (`RESEARCH_DEEP_EXECUTION`). Directive continuation runs deterministically inside the same continuation sweep that drives n8n.
