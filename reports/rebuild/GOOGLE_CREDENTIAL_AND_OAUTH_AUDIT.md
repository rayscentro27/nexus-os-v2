# Google Credential and OAuth Audit

Credential source: macOS keychain through Nexus credential control plane,
credential ID `credential.google.workspace.prod.v1`.

At implementation time client ID, client secret, and refresh token were
configured. Refresh-only credentials are constructed in memory; access tokens
are not persisted by the MCP server. No secrets were printed or committed.

The existing grant includes `gmail.readonly`, `calendar.events`, and
`drive.file`. Only Gmail and Calendar read methods are exposed in this phase;
Drive is not registered. The MCP server itself grants no authority.

`GOOGLE_CREDENTIAL_SOURCE=existing_keychain`
`CANONICAL_TOKEN_SOURCE=Nexus credential control plane`
`REFRESH_SUPPORTED=YES`
`SECRET_EXPOSURE=NO`
