# Nexus Automation Control Center

The Automation Control Center is the single place to see, per category, what Nexus can run
autonomously (Level 1), what is approval-gated (Level 2), and what is blocked (Level 3).

## Surfaces

- **Config:** `src/config/nexusAutomationStatusRegistry.ts` + `src/lib/nexusAutomationStatus.ts`.
- **Report generator:** `scripts/automation/generate_automation_control_report.py`.
- **Reports:**
  - `reports/runtime/automation_control_report_latest.json`
  - `reports/manual_publish/automation_control_report_latest.md`
  - `reports/runtime/nexus_automation_control_center_latest.json`
  - `reports/manual_publish/nexus_automation_control_center_latest.md`
- **Command Center:** `src/components/command-center/MissionControl.tsx` shows the Level 1/2/3
  counts, schedule-ready / connector / external-API counts, high-risk guard status, the top
  automation risk, and the next recommended safe automation.

## Run it (dry-run, local-first)

```
python3 scripts/automation/generate_automation_control_report.py --dry-run --json
```

The report includes: all categories, per-category Level 1/2/3 actions, what is schedule-ready,
what is disabled/blocked, what is safe to run manually, what needs a separate contract, what needs
a connector, what needs Ray approval, Hermes' recommended next automation, the top automation
risks, what Ray can ignore for now, and what should show in future UI.

## Safety

The report is read-only and deterministic. It never activates a scheduler, publishes, sends,
trades, spends, deploys, scrapes, downloads media, or calls external AI. "schedule_ready" means a
candidate exists — not that anything is running.
