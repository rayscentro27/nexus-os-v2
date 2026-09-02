# WP9I runtime provenance

The bridge and existing Telegram receipt contracts preserve the distinction
between transport, Nova identity, Hermes runtime, model route, authority, and
specialist execution. The new Oracle bridge records the configured model in
its request metadata and the real bridge proof identified:

```text
hermes_version=0.20.6
hermes_location=Oracle_existing_container
model_provider=OpenRouter
model=nvidia/nemotron-3.5-lightning:free
profile=nova_nexus_target_not_native_API_served
fallback_used=false
```

Because no Telegram cutover occurred, there is no genuine live Telegram
receipt with Oracle runtime provenance. That omission is intentional and is a
cutover blocker, not a missing claim.
