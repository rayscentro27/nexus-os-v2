# WP9I test matrix

| Test | Result |
|---|---|
| Existing credential discovery | PASS; Mac OpenRouter credential reused |
| Keychain bridge lookup | PASS; 2 unit tests |
| Oracle service restart | PASS; existing container remained 0.20.6 |
| Post-restart provider API | PASS_REAL; `ORACLE_NOVA_PERSISTENCE_OK` |
| Mac bridge health | PASS_REAL; HTTP 200, version 0.20.6 |
| Mac bridge model | PASS_REAL; `ORACLE_BRIDGE_MODEL_OK` |
| Bridge/Nova focused regression | PASS; 17 tests |
| Oracle MCP/skills/delegation | NOT_PROVEN; configuration prerequisite missing |
| Telegram cutover | NOT_RUN; failed closed by gate |
| WP9 scheduler/certification | PRESERVED; no scheduler mutation |
| Canonical build | BLOCKED; pre-existing Tailwind non-termination reproduced |
| Secret scan | PASS; no secret material added to repository |

The prior combined pytest hang was not reproduced by the isolated 17-test
suite; no runner lifecycle repair was required in this campaign.
