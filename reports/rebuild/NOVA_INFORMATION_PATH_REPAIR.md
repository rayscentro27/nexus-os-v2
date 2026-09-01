# Nova information-path repair

## Finding

The trace-proven defect was a mixed-semantics current opportunity envelope:
`historical_running_total` was copied from
`reports/hermes_modernization/live_research_decisions.json` into a result
otherwise labeled as a current opportunity view. Hermes correctly saw a fresh
MCP result and used the field; the label and placement made the historical
number salient for a current attention answer.

## Repair

Commit `a8557f3` removes only `historical_running_total` from the current
opportunity adapter output. It does not add Nova restrictions, phrase rules,
classifiers, templates, personality changes, or history deletion. The current
eligible items and classification/filter metadata remain available.

## Verification

Direct post-repair MCP output has zero eligible opportunities, filtered
historical records, and no `historical_running_total`. A Hermes-native
attention preflight using a clean session omitted 8,510. A contaminated-session
retest also omitted it from the final response despite old history still
containing the number.

Health claims remain fresh-MCP-supported and were not changed. The queued Voice
work-order claim remains current and supported.
