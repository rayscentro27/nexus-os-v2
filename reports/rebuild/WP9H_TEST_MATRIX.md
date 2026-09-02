# WP9H test matrix

| Test | Result | Evidence |
|---|---|---|
| Git/origin baseline | PASS | local and origin both `adb218f6f910b8cbfac7f12994f7542f6b25ab98` at audit start |
| Durable WP9 state read | PASS | `data/runtime/wp9_certification_state.json`, `RETRY_NIGHT_1` |
| Existing Oracle container inventory | PASS | live `nexus-hermes-0206`, version 0.20.6 |
| Authenticated Oracle health | PASS_REAL | HTTP 200, version 0.20.6 |
| Ephemeral Oracle model route | PASS_REAL | exact sentinel, 5.49 seconds |
| Durable Mac bridge auth | BLOCKED | no approved Mac bridge credential |
| Oracle Nova/context/MCP/skills/delegation | NOT_RUN/NOT_PROVEN | prerequisite route/profile gates incomplete |
| Telegram cutover | NOT_RUN | cutover gate correctly failed closed |
| Scheduler/certification continuity | PASS_PRESERVED | scheduler not stopped or modified; state not manually changed |
| Canonical build | PASS_PRIOR_VERIFIED | WP9G/WP9E verified; no source code changed in this audit |
| Secret scan | PASS_PRIOR_VERIFIED | no credential values added by this audit |

No engineering test was represented as scheduled autonomy evidence.
