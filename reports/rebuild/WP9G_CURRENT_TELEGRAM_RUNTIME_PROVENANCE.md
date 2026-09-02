# WP9G current Telegram runtime provenance

Live configuration was read from the launchd plist and canonical runtime env.

- Label: `com.nexus.telegram-hermes-nova`, 30-second interval, 14,211 runs,
  last exit 0.
- Runner: `scripts/ops/run_nova_with_runtime_env.sh`.
- Worker: `scripts/nova/nova_telegram_worker.py --once`.
- Primary flag: `NOVA_PRIMARY_RUNTIME=hermes`.
- Hermes execution: `scripts/nova/nova_hermes_shadow.py`, launched through the
  Mac `~/.hermes/hermes-agent` interpreter and `config/hermes/nova-profile`.
- Model route: OpenRouter, configured model `openai/gpt-4o-mini`.
- Telegram transport remains Mac-owned. Oracle tunnel exists separately but is
  not used by this subprocess.

Therefore current Telegram is Hermes-native, but not Oracle 0.20.6-backed.
