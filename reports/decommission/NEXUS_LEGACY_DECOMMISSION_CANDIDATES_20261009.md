# Nexus Legacy Decommission Candidates — 2026-10-09

No legacy environment is permanently deleted in this pass. The table records dependency and authority status from the already-certified recovery, runtime, secret, and deployment evidence. Local schedules/executors remain off. Remote Meta/Netlify uncertainty is isolated to the affected frontend/provider.

## A. SAFE_TO_REMOVE_NOW

None. Every candidate retains rollback, forensic, user-session, or external deployment value that requires archive or final signoff first.

## B. REMOVE_AFTER_META_REVOCATION

- `~/nexuslive` and old public build outputs: retain restricted forensic evidence until old Meta credential revocation and deployed artifact identity are confirmed.

## C. REMOVE_AFTER_NETLIFY/CLOUDFLARE_DECISION

- `~/nexuslive`: keep source and deployment metadata until production ownership and deployed commit are confirmed. No Cloudflare migration is part of this freeze.

## D. FORENSIC_RETENTION_ONLY

- `~/nexus-os-v2`, `~/.nexus`, `~/.hermes`, `~/.openclaw`, `~/.pm2`, legacy Telegram paths, old Research/WP9 loops, and old trading loops. Keep schedules/autostarts off and preserve logs/configuration as evidence.

## E. STILL_REQUIRED

- Disabled launchd definitions remain part of recovery/rollback evidence. Authenticated browser profiles remain user-owned and untouched; Nexus browser automation stays off.

## Controlled later candidates

- Secondary `.venv-agent-platform`: eligible for decommission only after checkout archive and a final no-consumer review.
- `credit_analysis_jobs` consumer: eligible for retirement only after the rollback window closes; preserve all 25 rows (13 queued) until separately approved.

## Dependency register

| Component | Classification | Last consumer / dependency | Secret / authority state | Decommission condition | Action now |
|---|---|---|---|---|---|
| `~/nexus-os-v2 secondary checkout` | FORENSIC_RETENTION_ONLY | No production runtime references; historical tooling only; No unique required code per prior closure evidence; preserve for rollback comparison | Legacy secret refs may remain in historical files; no active certified consumer | After immutable archive and final post-certification dependency signoff | Keep read-only/quarantined; do not delete now. |
| `~/nexuslive` | WAITING_ON_EXTERNAL_DEPENDENCY | Netlify production relationship is not fully admin-verified; Frontend/deployment ownership and public Meta exposure history | Old Meta identity is compromised; newer credential is server-side only | Meta old credential revoked and Netlify production owner/commit identified | Keep isolated; never build/publish the exposed artifact. |
| `~/.nexus` | FORENSIC_RETENTION_ONLY | Legacy tools only; certified runtime uses canonical config path; Historical local configuration and receipts | May hold legacy credential metadata/material; no active certified consumer | After secure metadata/receipt archive and credential consumer signoff | Restrict permissions and retain quarantined. |
| `~/.hermes` | FORENSIC_RETENTION_ONLY | Legacy Hermes runtime; internal Nexus cron inactive; Historical schedule/config evidence | Legacy credential scope may exist; runtime inactive | After schedule and secret metadata archive | Keep schedules disabled; no worker launch. |
| `~/.openclaw` | FORENSIC_RETENTION_ONLY | Legacy OpenClaw runtime; active jobs zero in prior certification; Historical schedule/job evidence | Legacy refs may exist; no active consumer | After schedule/secret metadata archive | Keep disabled and quarantined. |
| `~/.pm2` | FORENSIC_RETENTION_ONLY | Legacy process manager state; Nexus workflow executor count zero; Restart/log evidence | Potential process env metadata; no active executor | After PM2 dump/log metadata archive and no-consumer proof | Do not resurrect; retain evidence. |
| `Legacy launchd plists and disabled source definitions` | STILL_REQUIRED | Recovery verifier and rollback inventory; Canonical safe-boot verification | No active credential consumer | After a later approved decommission plan and replacement baseline | Leave disabled; retain source and evidence. |
| `Legacy Telegram/Nova poller paths` | FORENSIC_RETENTION_ONLY | None in certified execution; passive internal summary only; Legacy route evidence | Telegram credential must remain unavailable to legacy executors | After consumer graph and route archive retained | Keep code quarantined and schedules off. |
| `Old Research/WP9 persistent loops` | FORENSIC_RETENTION_ONLY | None in certified run; durable job handlers used; Historical operating-loop evidence | No active certified consumer | After archive and post-certification decommission review | Do not enable; retain disabled definitions. |
| `Old trading loops` | FORENSIC_RETENTION_ONLY | None; certification used local bounded replay only; Historical strategy and broker route evidence | Broker/live credentials unavailable to certification worker | After route/credential archive and explicit live-trading policy review | Keep disabled; live trading remains OFF. |
| `Authenticated browser profiles` | STILL_REQUIRED | Interactive user Chrome/Chrome Remote Desktop; User-owned interactive sessions | Session material must remain user-managed | No planned removal in this campaign | Preserve untouched; keep Nexus browser automation off. |
| `~/nexus-os-v2/.venv-agent-platform secondary Python environment` | READY_TO_DECOMMISSION | None in production; canonical venv is used; No production runtime reference per prior verified closure | Environment may contain packages/config only; no active secret consumer | After secondary checkout archive and operator review | Do not delete in this pass; candidate for later controlled removal. |
| `Legacy credit_analysis_jobs consumer` | READY_TO_DECOMMISSION | No active consumer; preserved queue remains unconsumed; Rollback window for document-upload durable-job migration | None known active | After whole-company certification plus approved rollback-window expiry | Keep table/data; prepare consumer retirement only after approval. |
| `Old nexuslive public build outputs containing compromised Meta identity` | WAITING_ON_EXTERNAL_DEPENDENCY | Public/deployed artifact status requires Netlify admin mapping; Forensic comparison and deployment identity | Compromised old Meta credential requires provider-side revocation | After secure evidence archive, Meta revocation, and deployment confirmation | Restricted forensic retention only; do not serve or rebuild. |
