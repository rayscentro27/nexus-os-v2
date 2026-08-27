# Nexus Remote Integrations Reconciliation

Redacted; no credential values are persisted.

- Netlify CLI/site: `PASS`
- Meta callback implementation: `True`
- Meta persistence: `NOT_CONFIGURED`
- Voice remote configuration: `PASS`
- External mutations: `0`

## Remote Variables

| Variable | Present | Source | |
|---|---|---|---|
| `CF_ACCESS_CLIENT_ID` | True | `NETLIFY_ENV` | |
| `CF_ACCESS_CLIENT_SECRET` | True | `NETLIFY_ENV` | |
| `VOICE_ACCESS_ORIGIN` | True | `NETLIFY_ENV` | |
| `GROQ_API_KEY` | True | `NETLIFY_ENV` | |
| `OPENROUTER_API_KEY` | True | `NETLIFY_ENV` | |

## Remaining Gates

- Meta webhook server secrets are not proven by current metadata; callback deployment and persistence remain gated.
- Voice remote health is untested because the relay requires an authenticated Nexus user request.
- Outbound social/email actions remain gated.
