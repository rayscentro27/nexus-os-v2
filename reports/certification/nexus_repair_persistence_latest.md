# Repair Persistence and Live Runtime Resolution

The live Telegram service is `com.nexus.telegram-hermes-nova`, launched from
the repository runner `scripts/nova/nova_telegram_worker.py`. The prior
resolver was wired only into the separate operations worker, so live Nova did
not use it consistently.

The canonical resolver now resolves explicit repair identifiers through
`get_repair()` before conversational/Product Evolution routing. Operational
lineage comes from governed work orders and approvals plus the repair runtime
state; `manual_e2e_latest.json` remains certification evidence, not the repair
database.

VOICE-001 resolves to work order
`wo_b5a3b90892804ec79164159997caf264`, run
`MANUAL-E2E-20260827-2992`, state `WAITING_WORKER`, access
`AVAILABLE_REMOTE_NETLIFY`, and deployment authority
`SEPARATE_APPROVAL_REQUIRED`.

No new repair, work order, approval, mission, deployment, email, social,
payment, or trading action was performed.
