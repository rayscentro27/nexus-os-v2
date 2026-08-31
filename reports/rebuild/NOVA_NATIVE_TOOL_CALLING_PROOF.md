# Native Tool-Calling Proof

## Intended shadow contract

```text
Hermes assistant tool_calls
→ Hermes tool executor/registry
→ bounded adapter or existing web provider
→ tool result in the same conversation
→ Hermes continuation
→ Nova final response
```

This replaces the custom text marker only inside the shadow. The current Nova
text-envelope parser remains untouched for rollback and A/B comparison.

| Assertion | Shadow implementation status |
|---|---|
| Native Hermes tool-call surface exists | IMPLEMENTED in installed Hermes |
| Custom envelope used by shadow | NO |
| Tool result continuation | PROVEN: web, Nexus, Alpha, and `delegate_task` returned tool results and continued |
| Raw tool envelope delivered to Ray | No Telegram delivery path exists in shadow |
| Authority boundary | Bounded adapter; no Nexus mutation |

Observed native calls included `nexus_read_shadow`, `alpha_challenge_shadow`,
`web_search`, `web_extract`, and `delegate_task`. The web calls returned
structured provider errors and still continued to a final Nova response.
