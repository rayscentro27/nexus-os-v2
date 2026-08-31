# Nova Telegram Shadow Exactly-Once Proof

The shadow receipt filename and run ID are deterministic: `ab-shadow-{telegram_update_id}.json`. Before invoking Hermes, the worker checks for that receipt and returns the existing record. This prevents a one-shot worker retry from creating a second shadow invocation for the same update. The canonical per-chat lock remains in place, and no second polling worker was created.

Focused tests prove one subprocess call for two calls with the same update, Hermes interpreter selection, no `OPENROUTER_API_KEY` in the child environment, retained primary/shadow IDs, and isolated shadow failure with zero shadow sends.

Development smoke receipts used update IDs 980001–980003. Each completed with `runtime_init=true`, `model_init=true`, and `shadow_telegram_send_count=0`.
