# Nexus Google MCP Read-Only Certification

## Result

`GOOGLE_MCP_RESTORE_STATUS=PARTIAL`

The governed bridge is restored at the architecture/tool-surface level, but
live Google Workspace reads are blocked by the existing refresh token being
rejected with `invalid_grant`. No OAuth flow was started and no scopes were
changed.

## Canonical architecture

Hermes `0.20.6` / `nova_nexus` runs on Oracle and reaches the Mac through the
existing authenticated Nexus Streamable HTTP MCP bridge. Google credentials
remain in the Nexus macOS Keychain control plane under
`credential.google.workspace.prod.v1`; they are not copied to Oracle, the
repository, or the browser.

The existing `services/google_mcp/server.py` remains the Google read
implementation. Its read-only tools are registered through the already
tunneled `services.nexus_mcp.server` surface so remote Hermes can call them
without a second Google control plane or a second OAuth store.

## Tool surface

Registered read-only tools:

- `gmail_search`, `gmail_read_message`, `gmail_read_thread`
- `calendar_search_events`, `calendar_read_event`, `calendar_get_availability`
- `drive_search`, `drive_read_file`

No send, label, archive, event mutation, upload, edit, share, move, or delete
tool is registered. Drive reads are bounded metadata reads, with opt-in text
extraction only for supported text-like files.

## Credential and scope boundary

Keychain presence was verified for `client_id`, `client_secret`, and
`refresh_token` without printing values. A direct bounded token refresh returned
`invalid_grant`. Therefore:

- Gmail, Calendar, and Drive are configured but not currently claimable as live
  capabilities.
- Existing configured scopes remain `gmail.readonly`, `calendar.events`, and
  `drive.file`; the broader historical grant was not invalidated.
- Read-only enforcement is at the Google MCP tool layer and MCP descriptions.
- Token reauthorization is required before live certification.
- No browser cookies, OAuth secrets, access tokens, or refresh tokens were
  written to the repository or report.

## Runtime and failure behavior

The Google bridge is reached through the existing Nexus MCP process/tunnel.
Google failures return bounded read-only error envelopes and do not grant
Hermes any mutation authority. The existing Nexus and Hermes runtimes remain
independent of the Google credential state.

The remote `nova_nexus` profile currently owns `nexus_mcp_remote`; Google is
therefore exposed through the canonical authenticated Nexus bridge rather than
by copying the local Keychain credential into the Hermes container.

## Certification evidence

| Area | Status | Evidence |
|---|---|---|
| Credential components | CONFIGURED | Keychain presence-only check |
| Token refresh | BLOCKED | Google token endpoint returned `invalid_grant` |
| Gmail live read | NOT CERTIFIED | Requires reauthorization |
| Calendar live read | NOT CERTIFIED | Requires reauthorization |
| Drive live read | NOT CERTIFIED | Requires reauthorization |
| Read-only tool registration | PASS_REAL | Nexus MCP registration and focused tests |
| Mutation blocking | PASS_REAL | Allowlist and absence of mutation tools |
| Credential redaction | PASS_REAL | Existing control-plane contract; no values in output |
| Google failure isolation | PASS_REAL_BOUNDED | Google calls produce bounded error envelopes |

Historical receipts include successful Gmail reads from September 1, but they
are not used as current certification evidence.

## Required human boundary

Ray must reauthorize the existing Google Workspace credential using the
approved Nexus authorization flow. After that, rerun the bounded Gmail,
Calendar, and Drive probes and the Hermes natural-language tool calls. Do not
broaden scopes unless a specific read operation proves it necessary.

## Changed architecture

- Added Drive metadata/text read tools to the existing Google MCP.
- Registered the existing Google read implementation through the canonical
  Nexus MCP bridge used by remote Hermes.
- Updated Nova capability truth to report the latest redacted Google health
  state rather than claiming Google is absent from the runtime.
- Added a bounded Drive-summary regression test.

No Hermes, Research, Alpha, SEO, UI, model routing, OAuth credential, or
external Google mutation behavior was changed.
