# WP9E Hermes Oracle staging

`HERMES_ORACLE_STAGING=NOT_EXECUTED_STAGING_IMAGE_NOT_SELECTED`.

The existing Oracle Hermes container and gateway are production-adjacent
infrastructure. No image pull, upgrade, restart, or cutover was performed in
this campaign. The existing container did provide the browser proof. A safe
next step is an explicitly isolated staging container with separate state,
ports, credentials and no scheduler authority, followed by adapter, MCP,
skill, browser and bounded delegation tests.
