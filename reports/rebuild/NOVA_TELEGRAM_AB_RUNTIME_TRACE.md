# Nova Telegram A/B runtime trace

Baseline: `f0b1259`  |  Campaign: `HG-WP6.5-NOVA-HERMES-NATIVE-TELEGRAM-A-B-CERTIFICATION-20260831-01`

The canonical Nova consumer is `scripts/nova/nova_telegram_worker.py`, launched
by `com.nexus.telegram-hermes-nova` through `run_nova_with_runtime_env.sh`.
The worker is one-shot and owns the Nova offset. The separate Hermes v2 service
is not a Nova consumer. No second Telegram bot or polling consumer was created.

An opt-in `NOVA_TELEGRAM_AB_CERTIFICATION=true` hook now runs the current custom
result first, invokes the silent Hermes shadow with the same text and a separate
shadow session, writes one A/B receipt, and sends only the custom response.
Shadow exceptions are isolated from primary delivery.

The flag was not enabled during this development turn, so no fabricated
Telegram message is counted as Ray evidence. Real A/B certification remains
pending Ray messages through the existing bot.
