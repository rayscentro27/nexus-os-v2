# Nexus MCP Follow-up Freshness Contract

Current-state questions are volatile reads. Hermes must call the relevant MCP
tool for a fresh present-state question instead of treating prior conversational
content as a current review, blocker, or opportunity result.

The review tool description explicitly identifies this behavior:

> Fresh volatile read: return only active Ray approvals requiring a decision.

No phrase router or classifier was added. Ordinary conversation remains
unchanged; freshness is expressed at the resource boundary and in receipts.

The isolated regression on 2026-08-31 showed the second review question made
zero MCP calls and reused the first turn's session context. The tool contract is
present, but native Hermes selection did not honor it in this run.

SECOND_TURN_NEXUS_GET_REVIEWS_EXECUTED=NO
FOLLOWUP_FRESHNESS_REGRESSION=FAIL
