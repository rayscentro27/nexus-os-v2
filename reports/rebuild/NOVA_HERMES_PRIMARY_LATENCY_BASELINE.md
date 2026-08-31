# Hermes Primary Latency Baseline

The final real A/B baseline was approximately:

- median Hermes shadow latency: 12.7 seconds
- maximum Hermes shadow latency: 81.7 seconds

Primary receipts preserve model/tool/total latency and tool-call telemetry.
Latency optimization is required as a follow-up operational campaign, but it
was not used as a correctness blocker because the primary preflight completed
successfully and the existing worker delivery boundary remained intact.

`LATENCY_OPTIMIZATION_REQUIRED=YES`
