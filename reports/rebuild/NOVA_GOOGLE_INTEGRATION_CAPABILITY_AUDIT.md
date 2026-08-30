# Nova Google Integration Capability Audit

No secrets are included. No Google operation was performed.

## Repository and certification evidence

Google Workspace code exists at `scripts/nexus_agent_platform/google_workspace.py`. It uses credential identifier `credential.google.workspace.prod.v1` and declares scopes `gmail.readonly`, `calendar.events`, and `drive.file`.

`reports/certification/nexus_calendar_authorization_latest.json` records:

- OAuth client: `CONFIGURED`
- refresh capability: `CONFIGURED`
- Gmail read: `PASS`
- Calendar read: `PASS`
- Drive read: `PASS`
- mutations performed: `false`
- secret values exposed: `false`
- publishing mode: `TESTING_OR_EXTERNALLY_MANAGED`

## Capability matrix

| Capability | Implemented | Configured | Authenticated/proven | Callable from Nova | Callable from Nexus |
|---|---|---|---|---|---|
| Gmail read | YES | YES | PASS in certification artifact | Not proven in live Telegram | Read path exists; live invocation not proven |
| Gmail send | Governed capability name exists in shared policy, but no Google send adapter found | N/A for direct adapter | Not proven | NO direct Nova write | GATED; no proven Google send adapter |
| Calendar read | YES | YES | PASS in certification artifact | Not proven in live Telegram | Read path exists; live invocation not proven |
| Calendar event creation | Capability/status model exists; no callable event-creation adapter found | OAuth scope is configured | Mutation not tested | NO proven callable path | NO proven callable path; gated |

The active-operator capability registry separately marks `email.send` as `GATED` and `calendar.mutate` as gated. This is an authority/execution boundary, not proof that Google has no read integration.

## Correct interpretation

The evidence supports:

- Google Workspace integration code exists.
- Gmail and Calendar read authorization was certified in the stored artifact.
- Direct email sending is not proven and remains gated.
- Calendar event creation is not proven and no adapter was found.
- Nova’s Telegram path did not prove it consulted live capability truth.

Therefore the observed claims “Nexus has no Google Email access” and “Nexus cannot schedule appointments” are overbroad when interpreted as claims about all Google access. The precise current answer is capability-specific and must distinguish read, draft/request, send, and event mutation.
