# Nexus External Connector Inventory

**Generated**: 2026-07-05

---

## Connector Status Summary

| Connector | Env Vars Present | Server/Client | Connected | Mode | Risk |
|-----------|-----------------|---------------|-----------|------|------|
| Netlify | Yes (deployed) | Server | Live | APPROVED_LIVE | Low |
| Supabase v2 | Yes (all keys) | Both | Configured | SANDBOX_TEST | Medium |
| Old Supabase | No active refs | N/A | Not connected | N/A | None |
| Resend/Email | Yes | Server | Configured | DRY_RUN | Low |
| Stripe/Billing | Partial (recovered) | Server | Configured | OBSERVE | Medium |
| Oanda/Demo | Yes | Server | Configured | SANDBOX_TEST | Low |
| TikTok/Social | No | N/A | Not built | N/A | None |
| Meta/Instagram | Yes | Server | Configured | DRY_RUN | Medium |
| YouTube API | Yes (.env.local) | Server | Configured | DRY_RUN | Low |
| NotebookLM | Local only | N/A | Manual only | OBSERVE | None |
| Firecrawl | Referenced in code | Server | Unknown | SANDBOX_TEST | Low |
| SearXNG | Referenced in code | Server | Unknown | SANDBOX_TEST | Low |
| OpenRouter | Yes | Server | Configured | SANDBOX_TEST | Low |
| Groq | Not found | N/A | Not configured | N/A | None |
| Ollama | Referenced in code | Server | Unknown (local) | SANDBOX_TEST | None |
| Brave Search | Referenced in edge | Server | Unknown | SANDBOX_TEST | Low |
| Tavily | Referenced in edge | Server | Unknown | SANDBOX_TEST | Low |
| SerpAPI | Referenced in edge | Server | Unknown | SANDBOX_TEST | Low |
| Telegram | Partial (recovered) | Server | Unknown | OBSERVE | Low |
| Gemini | Partial (recovered) | Server | Unknown | SANDBOX_TEST | Low |

---

## Detailed Connector Status

### Netlify
- **Status**: APPROVED_LIVE
- **Evidence**: Got Funding deployed, forms work, custom domain configured
- **Env vars**: Build config in `netlify.toml`
- **Functions**: 3 Netlify functions active (alpha-search, alpha-url-review, alpha-provider)
- **Next action**: Verify all function endpoints in production

### Supabase v2
- **Status**: SANDBOX_TEST (schema defined, live status unverified)
- **Env vars**: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — all set in `.env`
- **Tables**: 77 defined across 14 migrations
- **Edge functions**: 2 (hermes-chat, hermes-search)
- **RLS**: Enabled, admin policies defined
- **Next action**: Verify migrations applied, test live reads/writes

### Resend/Email
- **Status**: DRY_RUN (key present, sending untested)
- **Env vars**: `RESEND_API_KEY`, `RESEND_TO_EMAIL`, `RESEND_FROM_EMAIL` — all set
- **Next action**: Send test email in sandbox mode

### Stripe/Billing
- **Status**: OBSERVE (keys in recovered env, no active code)
- **Env vars**: `STRIPE_SECRET_KEY`, `VITE_STRIPE_PUBLISHABLE_KEY`, `VITE_STRIPE_PRICE_ELITE`, `VITE_STRIPE_PRICE_PRO` — in `.env.nexus.recovered.local`
- **Config**: `configs/stripe_product_registry.json` exists
- **Next action**: Verify Stripe keys are valid, test checkout flow

### Oanda/Demo
- **Status**: SANDBOX_TEST (demo account configured)
- **Env vars**: `OANDA_API_KEY`, `OANDA_ACCOUNT_ID`, `OANDA_ENV=practice`, `PAPER_ONLY=true`, `LIVE_TRADING=false`
- **Next action**: Verify demo account connectivity

### Meta/Instagram
- **Status**: DRY_RUN (tokens present, posting untested)
- **Env vars**: `META_PAGE_ACCESS_TOKEN`, `META_PAGE_ID`, `META_INSTAGRAM_ACCOUNT_ID`, `META_APP_ID`, `META_APP_SECRET` — all set
- **Seed data**: Facebook and Instagram accounts seeded in `supabase/seed/0001_social_accounts.sql`
- **Next action**: Test social post in sandbox mode

### YouTube API
- **Status**: DRY_RUN (key present, API calls untested at scale)
- **Env vars**: `YOUTUBE_API_KEY` — set in `.env.local`
- **Cache**: 5 channel/video metadata files in `data/cache/youtube/`
- **Next action**: Test API call with real channel query

### OpenRouter
- **Status**: SANDBOX_TEST (key present, LLM routing untested)
- **Env vars**: `OPENROUTER_API_KEY` — set in `.env`
- **Next action**: Test Alpha provider bridge

### Firecrawl
- **Status**: SANDBOX_TEST (referenced in code, key presence unknown)
- **Env vars**: `FIRECRAWL_API_KEY` — referenced in `vite.config.ts` but not in `.env`
- **Next action**: Add to `.env` if needed, test URL review

### SearXNG
- **Status**: SANDBOX_TEST (referenced in code, URL unknown)
- **Env vars**: `ALPHA_SEARXNG_URL` — referenced in `vite.config.ts` but not in `.env`
- **Next action**: Add to `.env` if needed, test search
