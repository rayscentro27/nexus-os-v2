# Phase 15C Telegram operator acceptance

The full 25-question operator contract is covered by deterministic routing and
canonical-read contract tests: Hermes **25/25**, Nova **25/25**. The matrix
checks capability selection, object taxonomy, source metadata, stale-study
precedence, no fabricated data, workforce/loop separation, and Nova's empty
write set.

Current canonical facts were read from the governed operational layer:

- Four controlled business loops are returned from `live_loop_results.json`.
- Codex, OpenCode, and the local worker are `AVAILABLE`; Kilo and MiMo are
  `INSTALLED_UNPROVEN`.
- Provider cost and confirmed revenue are both `$0`.
- Payment is `BLOCKED_UNTIL_TEST_KEYS_RECONCILED`; client journey is `NO_GO`.
- The production client read is correctly wired to Supabase and excludes demo /
  certification profiles, but this process had no Supabase credentials. The
  result is explicitly `UNAVAILABLE`, not an invented count.

The Hermes bridge `/status` command path passed, and Nova's worker `--test`
passed. A real inbound Telegram certification was not performed because it
requires Ray to send the messages; no fake update, bot `sendMessage`, or
production Telegram mutation was used. The exact manual checklist is recorded
in the JSON report.

Protected state: client portal **NONE**, production Telegram **NONE**, Nova
authority **UNCHANGED**, new tools installed **NONE**.
