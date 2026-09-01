# Nexus MCP Opportunity Currentness Repair

`live_research_decisions.json` is an accumulated research artifact, not a
current opportunity ledger by itself.

The current view applies source-age and record classification before exposing
items. The prior `running_total=8510` is retained only as historical context.
Records identified as `Item 0`, `Item 1`, or backed by `https://e.com/x` are
classified as synthetic and excluded.

Observed result:

- current eligible opportunities: `0`;
- historical records filtered: `8508`;
- synthetic records filtered: `2`.

ACCUMULATED_RESEARCH_COUNT_PRESENTED_AS_CURRENT=NO
SYNTHETIC_OPPORTUNITIES_PRESENTED_AS_REAL=0
