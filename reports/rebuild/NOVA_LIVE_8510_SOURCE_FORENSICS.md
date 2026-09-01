# Live 8,510 source forensics

The live attention turn was Telegram update `590357282`, message `1058`, with
parent Langfuse trace `d75a9b18dbf6d7496507a4a30c5999a9` and MCP trace
`71209c3dcc35fbade7ba25bd918af5a2`.

Before `a8557f3`, the fresh opportunity MCP result contained:

`data.historical_running_total = counts.running_total = 8510`

The source was `reports/hermes_modernization/live_research_decisions.json`,
whose source timestamp was `2026-08-27T16:54:23.025256+00:00`. Its semantic
meaning is the accumulated number of research candidates evaluated, not the
number of current opportunities. The record was historical/stale source data,
even though the current adapter exposed it alongside a current empty view.

The same value was also present in retained session assistant messages from
earlier opportunity turns. The 07:08 model-visible context therefore had two
paths to the number: the malformed current opportunity envelope and prior
conversation history. The primary source for the live claim was the fresh MCP
result; session history reinforced its salience.

The health claims were separate and supported by fresh MCP health data. No
shadow health path was involved.

## Result

This was a source-semantics/context-relevance defect, not a false historical
fact. The current opportunity adapter was repaired in `a8557f3` by removing the
historical accumulator from the current envelope. The ledger and historical
reasoning source were preserved.
