# Telegram Legacy Migration Plan

Current legacy worker: `scripts/operations/nexus_hermes_telegram_worker.py`.

Disposition: WRAP/MIGRATE incrementally. The existing worker, offset handling,
identity allowlist, and TruthKernel human-gate route are preserved. The new
department resolver is a closed-world compatibility layer for bounded intent
classes. Retirement is deferred until real Telegram E2E, failure recovery,
and receipt evidence pass.
