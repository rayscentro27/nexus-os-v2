# Nexus Production / Deployment Automation Policy

See [NEXUS_AUTOMATION_LEVELS.md](NEXUS_AUTOMATION_LEVELS.md).

- **Level 1 (autonomous):** deploy readiness reporting, internal checklists — no system change.
- **Level 2 (approval-gated):** production change proposals. Nexus may prepare them; Ray approves
  before any change.
- **Level 3 (blocked):** production deploys and destructive production actions. Blocked unless a
  separate design doc + safety contract + rollback plan + hard guard test is approved.

Automation never runs `git push`/deploy, never touches Netlify or live infra, and never creates
cron/launchd/systemd jobs. Deploys remain a manual, human-run step outside the automation surface.
