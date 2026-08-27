# Nexus Credential Recertification

Fully redacted post-Keychain-fix audit.

- registered identities: 19
- recovered after Keychain fix: 1
- still missing: 8

## Recovered After Keychain Fix

- `credential.google.workspace.prod.v1`: MISSING -> AVAILABLE via MACOS_KEYCHAIN

## Loop Readiness

| Loop | Credentials | Infrastructure | Authority | Operational now | Blocker |
|---|---|---|---|---|---|
| CONTINUOUS/AUTONOMY CORE | none | existing deterministic runtime | deterministic authority | YES | none |
| ACTIVE OPERATOR | credential.telegram.hermes.prod.v1, credential.supabase.admin.prod.v1 | existing operator/runtime paths | outbound communication governed | PARTIAL | no new credential blocker; outbound actions remain governed |
| FOREX MARKET DATA SCANNER | credential.oanda.market_data.practice.v1 | OANDA Practice read checks passed | practice/paper only; live disabled | YES | none |
| ORACLE GEMMA BACKGROUND REASONING | none | supervised private tunnel and Oracle Ollama | advisory only | YES | none |
| GENERAL WEB RESEARCH | credential.searxng.web_search.prod.v1, credential.brave.web_search.prod.v1 | SearXNG not installed; Brave configured | read-only | PARTIAL | SearXNG installation pending; Brave provider payment-limited |
| BRAVE WEB SEARCH | credential.brave.web_search.prod.v1 | adapter/canary exists | read-only | PARTIAL | provider HTTP 402/payment required |
| SEARXNG WEB SEARCH | credential.searxng.web_search.prod.v1 | not installed | read-only | NO | install/private endpoint approval required; base URL not yet applicable |
| GOOGLE WORKSPACE | credential.google.workspace.prod.v1 | live read certification passed | read-only application contract | YES | none |
| YOUTUBE RESEARCH | credential.google.youtube.prod.v1 | metadata connector available | read-only | PARTIAL | content/transcript scenario requires supplied URL and separate approval |
| HERMES TELEGRAM / MOBILE | credential.telegram.hermes.prod.v1 | existing Telegram runtime | outbound gated | PARTIAL | no credential blocker; outbound policy gate remains |
| SUPABASE ADMIN | credential.supabase.admin.prod.v1 | configured | admin gated | PARTIAL | application-specific approval gates |
| NETLIFY RELEASE | credential.netlify.release.prod.v1 | configured | release gated | PARTIAL | release authority intentionally gated |
| EMAIL / RESEND | credential.resend.email.prod.v1 | configured | outbound gated | PARTIAL | sending intentionally gated |
| SOCIAL / META | credential.meta.social.prod.v1 | configured | publishing gated | PARTIAL | publishing intentionally gated |
| VOICE / CLOUDFLARE | credential.cloudflare.voice_service.prod.v1 | local voice path exists | read-only transport | NO | Cloudflare voice credential missing; local voice can remain independent |
| STRIPE / PAYMENTS | credential.stripe.payments.test.v1 | test integration configured | payments disabled | NO | intentionally disabled; no credential action required |
| OPTIONAL EXTERNAL MODEL PROVIDERS | credential.openrouter.models.prod.v1, credential.openai.models.prod.v1, credential.groq.models.prod.v1, credential.google.gemini.prod.v1, credential.anthropic.models.prod.v1 | Oracle Gemma available | advisory/read-only | PARTIAL | optional providers missing; Oracle Gemma covers current reasoning lane |

## User Credential Actions

- none. Missing identities are optional, provider-blocked, or infrastructure/authority gates.

## Recommended Next Activation

Install SearXNG privately after the separate VM audit/installation approval; no credential is required before installation.
