# Affiliate/API Setup Center Report

> INTERNAL OPERATIONS — DRAFT ONLY — RAY REVIEW REQUIRED — NO REAL CLIENT DATA

| Connector | Status | Input later | Unlocks |
|---|---|---|---|
| NotebookLM export folder | configured and safe | `none` | Local research imports |
| Supabase | configured but disabled | `VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY` | Approved auth/storage; writes gated |
| Netlify | missing env var | `NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID` | Hosted previews |
| GitHub | unknown | `GITHUB_TOKEN or gh auth` | Remote automation |
| Cloudflare tunnel | missing env var | `CLOUDFLARE_TUNNEL_TOKEN` | Remote local access |
| Resend | configured but disabled | `RESEND_API_KEY` | Email; blocked this sprint |
| Meta/Facebook/Instagram | configured but disabled | `META_ACCESS_TOKEN, META_PAGE_ID` | Social; blocked |
| Google Search Console | missing key | `GOOGLE_SEARCH_CONSOLE_CREDENTIALS` | Measured SEO data |
| Google Analytics | missing key | `GOOGLE_ANALYTICS_PROPERTY_ID, GOOGLE_APPLICATION_CREDENTIALS` | Analytics evidence |
| YouTube API | unknown | `YOUTUBE_API_KEY` | Fresh metadata |
| Google Drive/manual export | missing account | `GOOGLE_DRIVE_FOLDER_ID` | Drive intake |
| Oanda practice | configured but disabled | `OANDA_API_TOKEN, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT` | Read-only demo checks |
| Ollama local | unknown | `OLLAMA_BASE_URL` | Local inference |
| Ollama cloud/Pro | missing key | `OLLAMA_API_KEY` | Hosted inference |
| OpenRouter | missing key | `OPENROUTER_API_KEY` | Hosted Alpha routing |
| Groq | missing key | `GROQ_API_KEY` | Fast inference |
| Stripe test mode | configured but disabled | `STRIPE_SECRET_KEY, VITE_STRIPE_PUBLISHABLE_KEY` | Test checkout; charges blocked |
| Firecrawl | future only | `FIRECRAWL_API_KEY` | Future extraction |
| n8n | future only | `N8N_API_KEY, N8N_BASE_URL` | Future orchestration |
| Postiz/Mixpost | future only | `SOCIAL_SCHEDULER_API_KEY` | Future social scheduling |

| Area | Value | Required now | Safety | Approval | Unlocks |
|---|---|---|---|---|---|
| credit monitoring | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
| online mailing | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
| business bank account | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
| business setup/LLC | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
| funding marketplace | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
| newsletter/email platform | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
| SEO/content tools | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
| AI tools | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
| trading education/tools | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
| tax/bookkeeping (future) | `[ENTER APPROVED URL]` | No | approval-gated | Yes | approved referral draft |
