# WP9I Oracle Nova provider evidence

The existing Oracle container remained `nexus-hermes-0206`, Hermes `0.20.6`.
Its active default provider was changed from unavailable local Ollama to the
already-authorized OpenRouter route using
`nvidia/nemotron-3.5-lightning:free`. The previous configuration was retained
as `/opt/data/config.yaml.wp9i-before-default-route` on Oracle.

The dedicated `/opt/data/profiles/nova_nexus` profile contains the Nova
identity, OpenRouter configuration, free-only auxiliary policy, and strict
permissions. The API profile-multiplex route did not pass profile-scoped API
key validation, so it was not used as cutover evidence.

Evidence:

- service restart completed successfully;
- Hermes version remained 0.20.6;
- authenticated health returned HTTP 200;
- post-restart API call returned `ORACLE_NOVA_PERSISTENCE_OK`;
- Mac bridge call returned `ORACLE_BRIDGE_MODEL_OK`.

`NOVA_LIVE_PROVIDER_NO_LONGER_DEPENDS_ON_OLLAMA=PASS`
`ORACLE_HERMES_DURABLE_RUNTIME=PASS`
`ORACLE_MODEL_EXECUTION_AFTER_RESTART=PASS_REAL`

Provider usage has no new account or subscription. Exact usage cost is not
available from the current route and remains UNKNOWN.
