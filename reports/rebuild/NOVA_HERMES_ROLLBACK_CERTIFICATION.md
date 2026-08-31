# Hermes Primary Rollback Certification

Rollback was tested as configuration only.

1. `NOVA_PRIMARY_RUNTIME=custom` loaded the historical custom graph and
   generated a response through the canonical worker delivery boundary.
2. `NOVA_PRIMARY_RUNTIME=hermes` was restored and generated a successful
   Hermes Nexus-read response through the same boundary.

`CUSTOM_ROLLBACK=PASS`, `ROLLBACK_CONFIGURATION_ONLY=YES`, and
`SOURCE_CODE_REVERT_REQUIRED=NO`.

Telegram bot identity, authorization, session namespaces, secrets, Nexus
authority, TruthKernel, Alpha lifecycle, and model/provider configuration were
not changed by rollback.
