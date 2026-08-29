# Hermes Tool-Provider Compatibility — 2026-08-29

All provider checks used existing configuration only. Secret values and
credentials are not recorded.

| Provider | Model | Reasoning | Tools accepted | Tool call emitted | Args valid | Hermes execution | Cost policy | Failure / disposition |
|---|---|---:|---:|---:|---:|---:|---|---|
| Oracle Ollama | `gemma3:4b` | PASS | NO | NO | N/A | NO | local/private | `INCOMPATIBLE_TOOLS`; retain for private reasoning |
| Groq | existing configured route | NOT_PROVEN | NOT_PROVEN | NO | N/A | NO | existing route | HTTP 403; `BLOCKED_CREDENTIAL` / external account state unresolved |
| OpenRouter | `google/gemma-4-31b-it:free` | PASS | YES | YES in direct probe | YES | rate-limited in worker | zero-priced route | HTTP 429 from upstream; `CERTIFIED_FALLBACK_TOOL_PROVIDER` at schema level, not selected for worker |
| OpenRouter | `minimax/minimax-m2.7:free` | PASS | YES | YES | YES | PASS | zero-priced route | governed Kanban canary completed; `CERTIFIED_PRIMARY_TOOL_PROVIDER` |

## Evidence

The direct OpenRouter probe used one harmless synthetic function schema and
verified a valid function name and argument object. A bounded Hermes Kanban
worker then accepted the task, used lifecycle tools, appended a result,
requested review, and was completed through the governed lifecycle. The task
remained `done` after a Hermes container restart and the API remained healthy.

OpenRouter is not made the global Hermes reasoning route. Oracle Ollama remains
the private reasoning route; the selected OpenRouter model is scoped to
tool-dependent worker tasks.
