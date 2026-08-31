# Nova Hermes Latency Before / After

Baseline commit: `227258e`

| Workload | Before evidence | After measured | Target | Result |
|---|---:|---:|---:|---|
| General/no-tool | ~10.25s median; 7–11s receipts | 7.48s | ≤8s | PASS |
| Nexus | Not separately instrumented | 16.93s | ≤10s | ABOVE GOAL |
| Web/current | 122.185s Tesla example | 25.91s Tesla run | ≤25s | NEAR GOAL |
| Multi-resource | Not separately instrumented | 39.43s | ≤35s | ABOVE GOAL |
| Alpha challenge | Not separately instrumented | 22.91s | ≤30s | PASS |
| Alpha reuse | No valid prior baseline | 6.21s same-session reuse | ≤8s | PASS |

`BEFORE_MEDIAN_LATENCY=10.25s` is the earlier production median supplied by the campaign. `BEFORE_MAX_LATENCY=122.185s` is the supplied Tesla production maximum; the earlier 60.74s affiliate case remains a separate known maximum. A statistically comparable production after median/max is not claimable from one local sample per workload.

Measured improvement is demonstrated for the Tesla representative: 122.185s → 25.91s. Global production median/max remain `NOT ESTABLISHED` pending a larger post-change receipt window.

