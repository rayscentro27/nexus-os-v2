# WP9N Single-tool Reliability

Five identical model-driven current-state probes produced:

| Attempt | Result | Latency |
|---:|---|---:|
| 1 | valid `DEGRADED` state and timestamp | 72.66s |
| 2 | `ReadTimeout` | 75.02s |
| 3 | `ReadTimeout` | 75.02s |
| 4 | valid `DEGRADED` state and timestamp | 35.40s |
| 5 | `ReadTimeout` | 75.03s |

`VALID_RUNS=2`, `MALFORMED_RUNS=0`, `TIMEOUT_RUNS=3`, `SUCCESS_RATE=40%`.

No malformed output reproduced. The observed failure class is upstream/API
timeout after tool-loop initiation, not a parser or schema defect. Therefore
`GPT4O_MODEL_DRIVEN_SINGLE_TOOL=NOT_RELIABLE_REPEATED_REAL`.
