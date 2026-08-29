# Nexus Credential Authority Reconciliation — 2026-08-29

## Result

The Keychain convention is consistent end-to-end. `store_keychain()`,
`keychain_status()`, and `_keychain_value()` address the same record:

- Service: `nexus/<credential_id>`
- Account: `<component>`

The convention is centralized in `_keychain_record()` and protected by a
round-trip regression test. The test proves STORE → STATUS=CONFIGURED → READ
for the same credential ID and component without writing a real Keychain
record or exposing the fixture value.

## Redacted registry inspection

| Credential | Registry status | Component status | Authority |
|---|---|---|---|
| `credential.google.workspace.prod.v1` | configured | `client_id`, `client_secret`, `refresh_token`: configured in macOS Keychain | read-only with governed test mutations |
| `credential.groq.models.prod.v1` | not configured through the canonical registry path | API key unavailable to this process | read-only |
| `credential.telegram.hermes.prod.v1` | configured | `bot_token`: configured in canonical runtime environment | gated outbound |

No secret values are included in this report.

## Certifications

- Google Workspace read-only: PASS; token refresh, Calendar event read, Gmail
  profile read, and Drive file-list read completed with no mutations.
- Hermes provider/tool capability: the local Ollama provider remains healthy
  for ordinary reasoning but does not support injected Kanban lifecycle tools;
  the existing Groq route returned HTTP 403. Tool-capable provider readiness
  remains blocked rather than being inferred from credential presence.
- Kanban worker: not resumed; its existing governed blocker is provider/tool
  compatibility, not the Keychain authority path.
- Active Operator: readiness dry-run and focused contract tests pass; the
  operator remains paused and no live cycle was activated.

## Verification

Focused credential, Google Workspace, Hermes plugin/provider, workforce, and
Active Operator tests passed. JSON validation and the repository secret scan
were run before checkpointing.
