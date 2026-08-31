# Hermes Primary Session Continuity

Hermes primary uses the stable session namespace
`nova-telegram-primary-{chat_id}`. Each worker invocation reopens the Hermes
sidecar session using that identifier, preserving Hermes conversational and
resource continuity across turns.

The custom Nova session namespace is not imported. This avoids reintroducing
stale custom capability beliefs while preserving the custom implementation as
a rollback option.

`HERMES_PRIMARY_SESSION_STABLE=YES`
`CUSTOM_STALE_MEMORY_IMPORTED=NO`
