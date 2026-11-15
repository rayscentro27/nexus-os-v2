# Nexus Trading Core R1 — Contabo placement (prepared, not deployed)

Status: **PREPARED / NOT DEPLOYED**. Nothing here is installed on Contabo by TRADING_ENGINE_RECOVERY_AND_PAPER_CERTIFICATION_R1.

## What runs here (lightweight, persistent operations)
One bounded cycle per completed H1 bar (systemd timer, `OnCalendar=*:00:30`). Each cycle runs these steps:
1. Refresh broker positions.
2. Reconcile.
3. Evaluate the frozen strategy, then the risk gate.
4. Execute, or stay observe-only.
5. Write performance.
6. Write the Nova summary.

- `MAX_ACTIVE_TRADING_STRATEGIES=1`
- `MAX_SIMULTANEOUS_TRADING_CERTIFICATION_JOB=1`: one container, `restart: "no"`, and the timer does not overlap.

## Resource limits (Contabo: 4 vCPU / 7.8 GiB / no swap; n8n + Postiz + REA 2.5 GiB present)
| Limit | Value |
|---|---|
| mem | 256 MiB hard, no swap |
| cpu | 0.5, `cpu_shares` 256 |
| pids | 64 |
| `oom_score_adj` | 700 (killed before Postiz/n8n) |
| filesystem | read-only rootfs; state volume only |
| expected cycle | under 10 s, ~40 MiB RSS, ≤ 12 OANDA requests |

## Not here (Kaggle / burst)
Large backtests, optimization, parameter sweeps, Monte Carlo, LEAN cross-engine validation, ML.

## Deployment prerequisites (later bounded task)
1. Live certification on Contabo, following the Mac R1 certification procedure.
2. Practice credentials in `secrets/oanda_practice.env` (0600).
3. A governor job context (`NEXUS_JOB_TYPE=TRADING_PAPER_CERTIFICATION`, or a dedicated paper job-type policy).
4. Owner approval of recurring practice orders before `--execute` and `paper_auto_execution_enabled=true`.

## Mac mini
No new Trading daemon is installed on the Mac. `com.nexus.forex-scanner.plist` and the `com.nexus.oanda-practice-trading` template are left untouched as rollback paths. They will be retired only after this runtime is certified on Contabo.
