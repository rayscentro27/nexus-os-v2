# Nova Layer Reduction Before/After

BEFORE_LAYER_COUNT=24
AFTER_LAYER_COUNT=5

## Reconciliation

| Current layer | Action |
|---|---|
| Telegram ingress | KEEP |
| authorization | KEEP |
| mission/receipt tracking | KEEP |
| chat lock | MOVE_TO_TOOL_BOUNDARY |
| preprocessing/salutation | MERGE into pre-model boundary |
| classify intent | MERGE into pre-model boundary |
| utility handling | MERGE into pre-model boundary |
| domain classification | MERGE into information plan |
| company question classification | MERGE into information plan |
| capability gate | MOVE_TO_TOOL_BOUNDARY for strict/factual reads |
| source policy | MERGE into information plan |
| truth view | MOVE_AFTER_MODEL |
| report quarantine | MOVE_AFTER_MODEL |
| company context | MERGE into context stage |
| capability discovery | MERGE into capability broker |
| skills/allowlist | MOVE_TO_TOOL_BOUNDARY |
| web search | MOVE_TO_TOOL_BOUNDARY |
| web retrieval | MOVE_TO_TOOL_BOUNDARY |
| Alpha | MOVE_TO_TOOL_BOUNDARY |
| Nexus reads | MOVE_TO_TOOL_BOUNDARY |
| Nexus delegation | MOVE_TO_TOOL_BOUNDARY |
| model routing | KEEP within model stage |
| post-validation | KEEP after model |
| fallback | MERGE with validation failure handling |
| session/memory composition | MERGE into composition stage |

Current graph count becomes five. The remaining operational boundaries are not
removed; they are combined by responsibility or enforced at invocation rather
than acting as independent model-interception layers.
