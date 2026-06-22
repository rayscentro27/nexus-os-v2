# Scheduler Policy

The old Nexus spammed Telegram because of **duplicate schedulers** and **per-event sends**.
Nexus OS v2 has exactly one of each.

## Rules
1. **One scheduler only.** One mechanism on one host (launchd OR cron OR systemd — not several).
   No duplicate jobs across checkouts. Document times here.
2. **All jobs write to `agent_jobs`.** Every run creates/updates a job row (queued → running →
   done/failed). No "invisible" automation.
3. **All visible work writes to `nexus_events`.** If it mattered, it's in the ledger.
4. **Telegram only through the guard + `telegram_messages`.** Every send (or suppression) is
   recorded as a row with a `message_hash`. No script sends to Telegram directly.
5. **One summary, never bursts.** A run that produces N items sends ONE summary, not N
   messages (the demo-trade spam lesson). Dedup window + per-purpose rate limits apply.
6. **Idempotency.** Every scheduled job takes a `run_lock` and uses a ledger `dedup` key so a
   double-fire cannot double-send or double-act.

## Job registry (filled as days land)
| Job | Lane | Schedule | Writes |
|---|---|---|---|
| _none yet_ | — | — | Day 2+ |

## Forbidden
- Duplicate launchctl/cron/systemd entries for the same job.
- Secrets embedded in unit files (load from `.env`).
- Any script that calls the Telegram API without the guard.
- Per-trade / per-item message bursts.
