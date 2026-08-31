# Nova Hermes Shadow Runtime Parity Repair

The prior in-process shadow call inherited the canonical Python 3.14 interpreter and failed before Hermes model initialization with `No module named 'openai'`.

Repair:

- `scripts/nova/nova_telegram_worker.py` invokes `scripts/nova/nova_hermes_shadow.py` with the existing Hermes interpreter at `~/.hermes/hermes-agent/venv/bin/python`.
- The canonical primary interpreter remains unchanged.
- The shadow remains opt-in under `NOVA_TELEGRAM_AB_CERTIFICATION=true` and has no Telegram send path.
- Timeout and non-zero exit are captured as shadow receipt errors; they do not interrupt primary delivery.
- Receipts record primary/shadow IDs, initialization, tools, results, and send counts.
- Shadow identity is deterministic per Telegram update (`ab-shadow-{update_id}`), making retries idempotent.

Development smoke calls through the worker boundary completed Hermes runtime/model initialization, public-web tool execution, and Nexus-read tool execution. No user-visible Telegram message was generated.
