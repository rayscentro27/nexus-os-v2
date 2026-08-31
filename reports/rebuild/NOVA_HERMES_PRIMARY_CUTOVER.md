# Nova Hermes Primary Cutover

Campaign: `HG-WP6.5-NOVA-HERMES-NATIVE-PRIMARY-CUTOVER-AND-ROLLBACK-CERTIFICATION-20260831-01`

## Decision

The canonical Nova worker now selects its primary runtime with
`NOVA_PRIMARY_RUNTIME`. The deployed value is `hermes`; supported rollback is
`custom`. Invalid values fail closed.

The Hermes primary invokes the already-certified Hermes runner through
`~/.hermes/hermes-agent/venv/bin/python`, while the canonical worker remains
the only Telegram consumer and delivery owner. Routine A/B fanout is disabled
after cutover with `NOVA_TELEGRAM_AB_CERTIFICATION=false`.

The custom graph remains present and selectable for emergency rollback. No
Telegram bot, model, provider, authority boundary, SOUL, or Nexus governance
was changed.

## Configuration

```text
NOVA_PRIMARY_RUNTIME=hermes
NOVA_TELEGRAM_AB_CERTIFICATION=false
```

The Hermes primary and prior shadow use the same runner, SOUL, model/provider,
native tools, evidence handling, and session-sidecar behavior.
