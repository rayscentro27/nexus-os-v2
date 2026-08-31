# Nova Hermes Communication Regression

The existing receipts show report-like output, schema headings, long tables, repeated framing, and recommendations delayed until late in the message. The cause was an underspecified model-facing conversational style contract; the native runner did not apply the existing non-native formatter.

The contract now preserves semantic report mode while specifying answer-first conversational output for ordinary Telegram turns. The code-level regression checks passed for evidence integrity and current-turn resource contracts. The local matrix produced direct recommendations for the comparison/choice prompts and retained truthful claim validation.

| Category | Before | After target assessment |
|---|---:|---:|
| Naturalness | 2/5 | 4/5 |
| Concision | 2/5 | 4/5 |
| Executive style | 2/5 | 4/5 |
| Mobile readability | 3/5 | 4/5 |
| Answer directness | 3/5 | 4/5 |
| Opinion clarity | 3/5 | 4/5 |
| Evidence clarity | 3/5 | 4/5 |

These are contract/regression scores, not human-rated Telegram production scores. `REPORT_STYLE_OVERUSE=NO` is satisfied by the explicit semantic report-mode exception in the prompt contract.

