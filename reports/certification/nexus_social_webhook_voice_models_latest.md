# Nexus Social, Webhook, Voice, and Model Reconciliation

Generated 2026-08-27. Redacted read-only certification; no external messages, posts, email, payments, or trades were sent.

## Results

| Capability | Credential / transport | Read or ingest result | Authority |
|---|---|---|---|
| Facebook | Page token present; Graph page read HTTP 200 | Page visible; Instagram business association present | Publishing gated |
| Instagram | Association present; no local webhook route found | Ingestion not proven | Publishing gated |
| Meta webhooks | One page subscription; fields inspected read-only | Callback/signature verifier missing in repository | Not ready |
| Telegram Hermes | Token present; `getMe` and `getWebhookInfo` HTTP 200 | Polling worker loaded; zero pending updates | Outbound governed |
| Resend | Key present; domains read HTTP 403 | Domain authentication not proven | Sending gated |
| Cloudflare Voice | Netlify relay exists and constructs Access headers | Local secrets absent; Netlify metadata command timed out | Remote reconciliation required |
| YouTube | Key present; approved metadata query HTTP 200 | One fixture item returned | Read-only ready |
| OpenRouter | Models endpoint HTTP 200 | 417 models, 21 free models; no paid inference | Read-only |
| Groq / Gemini | No approved credential found | Not enabled | Optional |

## Persistence and fixtures

The Supabase social schema and internal social connector proof exist. The fixture run created five approval-gated drafts and no public content. A real Meta webhook-to-Supabase consumer readback is not proven because no callback/signature route exists in the repository.

## Remaining genuine actions

1. Confirm the existing production Netlify environment metadata path if Voice transport certification is needed.
2. Add/deploy the governed Meta webhook callback with verify-token and signature validation before claiming Messenger or Instagram ingestion readiness.

Outbound social publishing, email sending, payments, and live trading remain disabled.
