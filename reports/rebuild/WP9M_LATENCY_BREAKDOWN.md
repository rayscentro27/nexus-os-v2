# WP9M Latency Breakdown

The Hermes API exposed total request latency and tool receipts, but did not
emit a reliable phase-by-phase timing record through the existing bridge.
Measured totals:

| Probe | Model | Total |
|---|---|---:|
| Specialist | gpt-4o-mini | 37.19s |
| Sequential current state | gpt-4o-mini | 27.21s |
| Multi-step opportunity | gpt-4o-mini | 38.16s |
| Nemotron multi-step comparison | Nemotron free | 120.31s timeout |

`LATENCY_BREAKDOWN=PASS_REAL_MEASURED_TOTALS;PHASE_TIMERS_UNAVAILABLE`.
