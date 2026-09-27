# Nexus Continuous Research Two-Hour Reporting — 2026-09-27

## Workstream A result

The existing canonical Research service is running from
`/Users/raymonddavis/nexus-os-v2-canonical` under the single LaunchAgent
`com.nexus.continuous-loop`. Its observed PID was 66857, with `KeepAlive=true`,
real execution mode, an active heartbeat, and a persisted next wake. No second
Research runner was created or started.

The new observer is `com.nexus.research-two-hour-report`. It is a separate
calendar-triggered LaunchAgent at two-hour intervals. It only reads heartbeat,
program, queue, execution, Alpha, handoff, and return records. It does not
select work, claim queue items, consume jobs, change scheduling, or stop
Research. The canonical on-demand command is:

```text
python3 scripts/research/generate_research_status_report.py --window-hours 2 --output latest
```

## First real report

Path: `reports/research/two_hour/latest.md`

Window: `2026-09-27T15:10:12Z` through `2026-09-27T17:10:12Z`.

Persisted evidence counted 11 source acquisitions with content, 11 substantive
findings, 11 AI interpretations, 0 Alpha reviews, and 0 department handoffs in
the window. Three acquisition results were degraded. The report does not count
queue creation, source selection, scheduler wakes, or metadata-only events as
substantive findings. Cumulative today reported 20 sources/findings, 20 AI
analyses, and 2 Alpha reviews, both `RESEARCH_MORE`.

The report preserves separate counters for YouTube selection, transcript stages,
AI analysis, evidence, Alpha, handoffs, returns, failures, and no-ops. It also
records the supported existing program scope without creating another registry.

## Workstream A safety

No customer messages, paid services, public publishing, lender applications,
fund transfers, or trades were performed. Historical report files are written
under `reports/research/two_hour/` with `latest.md` and `latest.json` pointers.
