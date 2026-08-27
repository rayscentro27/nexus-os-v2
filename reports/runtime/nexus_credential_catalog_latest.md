# Nexus Credential Catalog

Redacted identity inventory; secret values are never written.

| Identity | Provider | Components | Sources | Result |
|---|---|---|---|---|
| credential.brave.web_search.prod.v1 | brave | api_key:PRESENT | CANONICAL_RUNTIME_ENV | AUTH_REQUIRED |
| credential.google.workspace.prod.v1 | google | client_id:MISSING, client_secret:MISSING, refresh_token:MISSING | none | MISSING |
| credential.google.youtube.prod.v1 | google | api_key:PRESENT | CANONICAL_RUNTIME_ENV | AVAILABLE |
| credential.oanda.market_data.practice.v1 | oanda | account_id:PRESENT, api_token:PRESENT, environment:PRESENT | CANONICAL_RUNTIME_ENV | AVAILABLE |
| credential.telegram.hermes.prod.v1 | telegram | bot_token:PRESENT | CANONICAL_RUNTIME_ENV | AVAILABLE |
| credential.cloudflare.voice_service.prod.v1 | cloudflare | client_id:MISSING, client_secret:MISSING | none | MISSING |
| credential.supabase.admin.prod.v1 | supabase | url:PRESENT, service_role_key:PRESENT | CANONICAL_RUNTIME_ENV | AVAILABLE |
| credential.netlify.release.prod.v1 | netlify | auth_token:PRESENT | CANONICAL_RUNTIME_ENV | AVAILABLE |
| credential.stripe.payments.test.v1 | stripe | secret_key:PRESENT | CANONICAL_RUNTIME_ENV | AVAILABLE |
| credential.resend.email.prod.v1 | resend | api_key:PRESENT | CANONICAL_RUNTIME_ENV | AVAILABLE |
| credential.openai.models.prod.v1 | openai | api_key:MISSING | none | MISSING |
| credential.openrouter.models.prod.v1 | openrouter | api_key:PRESENT | CANONICAL_RUNTIME_ENV | AVAILABLE |
| credential.groq.models.prod.v1 | groq | api_key:MISSING | none | MISSING |
| credential.google.gemini.prod.v1 | gemini | api_key:MISSING | none | MISSING |
| credential.anthropic.models.prod.v1 | anthropic | api_key:MISSING | none | MISSING |
| credential.meta.social.prod.v1 | meta | page_access_token:PRESENT | CANONICAL_RUNTIME_ENV | AVAILABLE |
