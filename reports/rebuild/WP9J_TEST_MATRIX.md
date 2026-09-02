# WP9J test matrix

| Check | Result |
|---|---|
| Oracle service health after restart | PASS_REAL; HTTP 200, Hermes 0.20.6 |
| `nova_nexus` profile authentication | PASS_REAL; HTTP 200 |
| `nova_nexus` model list | PASS_REAL; HTTP 200 |
| `nova_nexus` model execution | PASS_REAL; exact `WP9J_PROFILE_MODEL_OK` |
| Nexus context on Oracle | NOT_PROVEN |
| Oracle MCP execution | NOT_PROVEN |
| Oracle skill execution | NOT_PROVEN |
| Oracle delegation | NOT_PROVEN |
| A/B harness | INELIGIBLE |
| Telegram cutover | NOT_RUN; fail closed |
| Scheduler | PRESERVED; no scheduler mutation |
| WP9 certification | PRESERVED; state unchanged by engineering |
| Canonical build | PASS from WP9I verified build; no source change in WP9J |
| Secret scan | PASS for scoped repository changes |

