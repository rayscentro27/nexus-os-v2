# Nova model-visible context inventory

For the 07:08 live attention turn, observable context included:

| Source | Classification | Visible | Contained 8,510 |
|---|---|---:|---:|
| Dedicated Nova SOUL/profile | stable identity | yes | no |
| Hermes conversation history | historical/session context | yes | yes |
| Prior assistant opportunity answers | historical claims | yes | yes |
| Prior tool-result index | prior volatile provenance | yes | indirectly |
| Fresh opportunity MCP result (pre-`a8557f3`) | mixed current/history envelope | yes | yes |
| Fresh health/reviews/blockers/work-items MCP results | current operational state | yes | no |
| Global Hermes SOUL/memory | excluded | no | no |
| Nexus shadow adapter | not executed | no | no |

Langfuse recorded prior assistant/tool counts and the dedicated profile hash;
the bounded session sidecar supplied the historical assistant text. No chain of
thought was captured.

After `a8557f3`, the current opportunity result contains zero eligible items and
filter counts but no `historical_running_total`. Retained history remains
available for historical questions and explanation.
