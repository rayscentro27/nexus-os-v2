# Nova Hermes Primary Latency Forensics

Campaign: `HG-WP6.5-NOVA-HERMES-PRIMARY-LATENCY-AND-COMMUNICATION-QUALITY-OPTIMIZATION-20260831-01`
Baseline: `227258e`

## Observed evidence

Existing primary receipts reported 7–11 seconds for no-tool turns, 13.106 seconds for the comparison turn, 60.7 seconds for a seven-call affiliate research turn, and 122.185 seconds for Tesla research. Those receipts had aggregate latency only.

The post-change runner now records phase data. Local Hermes-primary measurements (no Telegram delivery) were:

| Workload | Total | Subprocess/Hermes init | Model calls / model total | Tools | Search | Retrieval | Continuations |
|---|---:|---:|---:|---:|---:|---:|---:|
| No-tool reasoning | 7.48s | 3.43s | 1 / 2.85s | 0 | 0 | 0 | 0 |
| Nexus read | 16.93s | 1.54s | 3 / 14.49s | 6 | 0 | 0 | 2 |
| Current web (Tesla) | 25.91s | 1.51s | 1 / 23.48s | 4 | 0.50s | 7.90s | 0 |
| Nexus + web | 39.43s | 1.55s | 4 / 36.96s | 10 | 2.21s | 0.73s | 3 |
| Alpha challenge | 22.91s | 1.50s | 1 / 20.44s | 1 | 0 | 0 | 0 |
| Alpha follow-up reuse | 6.21s | 1.48s | 2 / 3.78s | 0 | 0 | 0 | 1 |

The Nexus and multi-resource results exposed existing continuation/tool-loop pressure; the evidence validator false-positive for a direct Nexus current-turn result was corrected. No evidence supports changing the certified subprocess boundary: initialization is about 1.5s after the first run and is not the dominant cost except as a small no-tool share.

`SUBPROCESS_OVERHEAD_SIGNIFICANT=NO`.

