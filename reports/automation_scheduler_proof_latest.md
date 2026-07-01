# Automation Scheduler Proof Latest

**Generated:** 2026-07-01T19:45:00Z
**Data Sources:** nexus_scheduler_inventory, nexus_operations_status

---

## Summary

| Status | Count |
|--------|-------|
| Total schedulers | 31 |
| Installed & Loaded | 28 |
| Installed & Not Loaded | 3 |
| Active Now (with PID proof) | 0 |

**Critical:** launchd loaded state is NOT proof of active execution. Process proof (PID) is separate from scheduler state.

---

## Scheduler Proof Details

### Loaded Schedulers (28)

| Scheduler | Last Output | Risk | Process Proof |
|-----------|-------------|------|---------------|
| ai.nexus.control-center | 2026-06-30T23:37:27Z | Low | None |
| ai.nexus.email-pipeline | 2026-07-01T19:35:35Z | Low | None |
| com.nexus.auto-executor | 2026-07-01T19:39:10Z | Medium | pid-607 (separate) |
| com.nexus.autonomy-worker | 2026-07-01T19:39:18Z | Low | None |
| com.nexus.cloudflare-tunnel | 2026-06-30T23:39:15Z | Low | pid-587 (separate) |
| com.nexus.continuous-ops-daily | 2026-07-01T14:00:07Z | Low | None |
| com.nexus.coordination-worker | 2026-07-01T19:30:08Z | Low | None |
| com.nexus.daily-operating | 2026-07-01T15:01:59Z | Low | None |
| com.nexus.demo-trading-loop | 2026-07-01T19:01:01Z | Medium | None |
| com.nexus.evening-closeout | 2026-07-01T01:00:35Z | Low | None |
| com.nexus.mac-mini-worker | 2026-06-30T23:37:36Z | Low | None |
| com.nexus.monetization-research | 2026-06-08T12:03:05Z | Low | None |
| com.nexus.monitoring-worker | 2026-07-01T19:36:58Z | Low | None |
| com.nexus.ollama | 2026-07-01T19:39:29Z | Low | Endpoint responding |
| com.nexus.ops-control-worker | 2026-07-01T19:36:02Z | Low | None |
| com.nexus.orchestrator | 2026-07-01T19:37:40Z | Low | pid-582 (separate) |
| com.nexus.research-signal-bridge | 2026-07-01T19:39:30Z | Low | pid-598 (separate) |
| com.nexus.research-worker | 2026-06-30T23:37:40Z | Low | pid-586 (separate) |
| com.nexus.signal-review | 2026-07-01T19:21:54Z | Low | None |
| com.nexus.signal-router | 2026-07-01T19:00:03Z | Low | pid-580 (separate) |
| com.nexus.strategy-lab | 2026-07-01T17:21:33Z | Low | None |
| com.nexus.tournament | 2026-07-01T19:38:00Z | Low | pid-622 (separate) |
| com.nexus.trading-engine | 2026-07-01T19:01:00Z | Medium | pid-588 (separate) |
| com.nexus.youtube-channel-poller | 2026-07-01T15:40:23Z | Low | None |
| com.raymonddavis.nexus.control-center | 2026-07-01T19:39:26Z | Low | pid-8840 (separate) |
| com.raymonddavis.nexus.dashboard | 2026-06-30T23:40:37Z | Low | pid-590 (separate) |
| com.raymonddavis.nexus | 2026-06-30T23:22:55Z | Low | None |
| com.raymonddavis.nexus.scheduler | 2026-06-30T22:28:42Z | Low | None |

### Not Loaded Schedulers (3)

| Scheduler | Last Output | Status |
|-----------|-------------|--------|
| com.nexus.hermes-status | 2026-04-22T17:11:59Z | Old log |
| com.raymonddavis.nexus.hermes-mobile | 2026-06-18T05:55:43Z | Old log |
| com.raymonddavis.nexus.telegram | 2026-05-15T00:10:24Z | Very old log |

---

## Proof Distinction

- **Loaded** = plist registered with launchd (loaded state)
- **Running** = actively executing right now (requires PID proof)
- **Last Output** = timestamp of most recent log entry
- **Process Proof** = PID found in `ps -axo` output (separate from scheduler state)

## Critical Note

Do not claim a scheduler is running without process/log proof. Loaded means the plist is registered with launchd, not that it is currently executing.
