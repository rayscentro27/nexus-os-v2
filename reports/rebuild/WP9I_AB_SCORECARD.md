# WP9I Nova A/B scorecard

The complete same-input A/B suite was not run because Oracle MCP, skills,
context, and delegation were not yet real execution paths. Comparing the
current live Mac brain against a model-only Oracle endpoint would not be a
valid A/B certification.

| Gate | Mac 0.14 path | Oracle 0.20.6 path |
|---|---|---|
| Model response | PROVEN | PROVEN after restart |
| Current Nexus context | PROVEN existing path | NOT PROVEN |
| MCP/skills | PROVEN existing path | NOT PROVEN |
| Delegation | PROVEN existing path | NOT PROVEN |
| Telegram continuity | LIVE | NOT CUT OVER |
| Cost | Existing route; exact usage UNKNOWN | Existing route; exact usage UNKNOWN |

`AB_CURRENT_PATH_SCORE=NOT_RUN`
`AB_ORACLE_0206_SCORE=INELIGIBLE`
`AB_WINNER=NO_DECISION_CURRENT_PATH_RETAINED`
