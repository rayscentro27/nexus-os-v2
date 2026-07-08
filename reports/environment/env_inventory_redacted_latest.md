# Environment Inventory (Redacted)

**Generated:** 2026-07-07  
**Note:** Values are NEVER printed. Only presence/status is reported.

## Primary Repo: ~/nexus-os-v2

### .env

| Key | Status |
|-----|--------|
| VITE_SUPABASE_URL | FOUND |
| VITE_SUPABASE_ANON_KEY | FOUND |
| SUPABASE_SERVICE_ROLE_KEY | FOUND |
| SUPABASE_ACCESS_TOKEN | MISSING |
| SUPABASE_DB_PASSWORD | MISSING |
| VITE_STRIPE_PUBLISHABLE_KEY | MISSING |
| VITE_STRIPE_PRICE_ID | MISSING |
| VITE_STRIPE_PRODUCT_ID | MISSING |
| STRIPE_SECRET_KEY | MISSING |
| STRIPE_WEBHOOK_SECRET | MISSING |
| RESEND_API_KEY | FOUND |
| RESEND_FROM_EMAIL | FOUND |
| TELEGRAM_BOT_TOKEN | MISSING |
| BRAVE_API_KEY | MISSING |
| META_ACCESS_TOKEN | MISSING |
| FACEBOOK_PAGE_ACCESS_TOKEN | MISSING |
| INSTAGRAM_ACCESS_TOKEN | MISSING |
| YOUTUBE_API_KEY | MISSING |
| NETLIFY_AUTH_TOKEN | MISSING |
| NETLIFY_SITE_ID | MISSING |

### .env.local

| Key | Status |
|-----|--------|
| YOUTUBE_API_KEY | FOUND |

### .env.nexus.recovered.local

| Key | Status |
|-----|--------|
| VITE_STRIPE_PUBLISHABLE_KEY | FOUND |
| STRIPE_SECRET_KEY | FOUND |
| TELEGRAM_BOT_TOKEN | FOUND |

## Legacy Repos

### ~/nexus-ai/.env

| Key | Status |
|-----|--------|
| SUPABASE_SERVICE_ROLE_KEY | FOUND |
| STRIPE_SECRET_KEY | FOUND |
| RESEND_API_KEY | FOUND |
| TELEGRAM_BOT_TOKEN | FOUND |

### ~/nexuslive/.env

| Key | Status |
|-----|--------|
| VITE_SUPABASE_URL | FOUND |
| VITE_SUPABASE_ANON_KEY | FOUND |
| VITE_STRIPE_PUBLISHABLE_KEY | FOUND |
| STRIPE_SECRET_KEY | FOUND |

### ~/nexus-ai-council-sandbox/.env

| Key | Status |
|-----|--------|
| TELEGRAM_BOT_TOKEN | FOUND |

## Summary

| Category | Found | Missing |
|----------|-------|---------|
| Supabase | 3 | 2 |
| Stripe | 3 | 3 |
| Resend | 2 | 0 |
| Telegram | 2 | 0 |
| Social | 1 | 3 |
| Netlify | 0 | 2 |
| **Total** | **11** | **10** |

## Conflicts

- Stripe keys exist in `.env.nexus.recovered.local` but not in `.env`
- TELEGRAM_BOT_TOKEN exists in `.env.nexus.recovered.local` but not in `.env`
- Legacy repos have some overlapping keys (not used for client portal)

## Recommendation

Move Stripe and Telegram keys from `.env.nexus.recovered.local` to `.env` when ready to use them.
